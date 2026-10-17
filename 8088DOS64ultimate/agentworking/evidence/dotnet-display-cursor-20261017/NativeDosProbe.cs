using System.Buffers.Binary;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using ViceTasks.Ultimate;

static class NativeDosProbe
{
 public static async Task<int> Run(UltimateClient client,JsonElement config,string output,CancellationToken token)
 {
  int diag=config.GetProperty("diag").GetInt32(),busy=config.GetProperty("disk_busy").GetInt32(),serial=0;
  int started=config.GetProperty("runtime_started").GetInt32(),nmi=config.GetProperty("native_nmi").GetInt32();
  bool display=config.TryGetProperty("capture_display_state",out var captureDisplay)&&captureDisplay.GetBoolean();
  bool displayOnly=config.TryGetProperty("display_check_only",out var displayCheck)&&displayCheck.GetBoolean();
  int cgaState=display?config.GetProperty("cga_state").GetInt32():0,renderRequest=display?config.GetProperty("render_request").GetInt32():0;
  var source=File.ReadAllBytes(config.GetProperty("runtime_prg").GetString()!);var start=File.ReadAllBytes(config.GetProperty("start_prg").GetString()!);var home=config.GetProperty("home").GetString()!;
  async Task<byte[]> Read(int a,int n){var b=await client.ReadMemoryAsync(a,n,token);if(b.Length!=n)throw new InvalidDataException("Short C64 read");return b;}
  async Task Write(int a,byte[] b)=>await client.WriteMemoryInlineAsync(a,b,token);
  void Save(string name,byte[] b)=>File.WriteAllBytes(Path.Combine(output,name),b);
  async Task Ready(){byte[]? old=null;for(int i=0;i<60;i++){await client.PauseAsync(token);var b=await Read(0,2048);var row=b[0xd6];var pointer=b[0xd1]|b[0xd2]<<8;bool ok=b[0x288]==4&&b[0x289]==10&&row is >0 and <25&&b[0xd3]==0&&pointer==0x400+40*row&&b[0xc6]==0;
    if(ok){var previous=b.AsSpan(pointer-40,40).ToArray().Select(x=>(byte)(x&127)).ToArray();ok=previous.SequenceEqual(new byte[]{18,5,1,4,25,46}.Concat(Enumerable.Repeat((byte)32,34)))&&b.AsSpan(pointer,40).ToArray().All(x=>(x&127)==32);}
    if(ok&&old!=null&&!old.AsSpan(0xa0,3).SequenceEqual(b.AsSpan(0xa0,3))){Save("BASIC-ready.bin",b);return;}old=ok?b:null;await client.ResumeAsync(token);await Task.Delay(100,token);}throw new TimeoutException("BASIC not ready");}
  async Task<byte[]> Command(byte op,ushort? key=null,int? address=null,int count=0){
   for(var tries=0;;tries++){
    await client.PauseAsync(token);var b=await Read(diag,19);if(b[0]==0xe1||b[3]!=0)throw new InvalidDataException("Native failure or outstanding command: "+Convert.ToHexString(b));
    if(op!=2||(await Read(busy,1))[0]==0)break;await client.ResumeAsync(token);if(tries==299)throw new TimeoutException("Disk operation remained active");await Task.Delay(100,token);
   }
   await Write(diag+4,new byte[]{0});if(key.HasValue)await Write(diag+5,BitConverter.GetBytes(key.Value));
   if(address.HasValue){var a=address.Value;await Write(diag+14,new[]{(byte)a,(byte)(a>>8),(byte)(a>>16),(byte)count,(byte)(count>>8)});}
   await Write(diag+3,new[]{op});var published=await Read(diag,19);if(published[3]!=op||published[4]!=0)throw new InvalidDataException("Native publication differs");
   if(key.HasValue&&BinaryPrimitives.ReadUInt16LittleEndian(published.AsSpan(5))!=key.Value)throw new InvalidDataException("Native key body differs");
   if(address.HasValue&&(published[14]!=(byte)address.Value||published[15]!=(byte)(address.Value>>8)||published[16]!=(byte)(address.Value>>16)||BinaryPrimitives.ReadUInt16LittleEndian(published.AsSpan(17))!=count))throw new InvalidDataException("Native read body differs");
   await client.ResumeAsync(token);
   var end=Stopwatch.StartNew();while(end.Elapsed<TimeSpan.FromSeconds(12)){var b=await Read(diag,19);if(b[0]==0xe1)throw new InvalidDataException("Native failure "+Convert.ToHexString(b));if(b[3]==0&&b[4]!=0){if(b[4]!=0xa5)throw new InvalidDataException("Native command rejected "+Convert.ToHexString(b));return b;}await Task.Delay(20,token);}throw new TimeoutException("Native command ACK; no retry");
  }
  async Task<byte[]> Guest(int address,int count){var bytes=new List<byte>();while(count>0){int n=Math.Min(Math.Min(count,2048),0x10000-(address&0xffff));var ack=await Command(4,address:address,count:n);if(ack[0]!=5)throw new InvalidDataException("Guest read not paused");bytes.AddRange(await Read(0xc100,n));address+=n;count-=n;}return bytes.ToArray();}
  async Task<(string text,int cols)> Snapshot(string label){await Command(2);var bda=await Guest(0x400,256);int cols=BinaryPrimitives.ReadUInt16LittleEndian(bda.AsSpan(0x4a)),offset=BinaryPrimitives.ReadUInt16LittleEndian(bda.AsSpan(0x4e));if(cols is not(40 or 80)||offset+cols*50>0x4000)throw new InvalidDataException("Guest BDA video geometry");var video=await Guest(0xb8000+offset,cols*50);var text=string.Join('\n',Enumerable.Range(0,25).Select(y=>new string(Enumerable.Range(0,cols).Select(x=>{int c=video[(y*cols+x)*2];return c is >=32 and <=126?(char)c:' ';}).ToArray())));var tag=$"{++serial:D3}-{label}";Save(tag+"-BDA.bin",bda);Save(tag+"-CGA.bin",video);File.WriteAllText(Path.Combine(output,tag+".txt"),text);Save(tag+"-C64-bitmap.bin",await Read(0x6000,8000));Save(tag+"-C64-matrix.bin",await Read(0x4000,1000));
   if(display){Save(tag+"-CGA-state.bin",await Read(cgaState,22));Save(tag+"-blink.bin",await Read(renderRequest+1,1));if(serial==1)Save("native-fonts.bin",await Read(0x4400,3072));}
   await Command(3);return(text,cols);}
  async Task<(string text,int cols)> WaitText(string label,Func<string,int,bool> predicate,int seconds=90){var end=Stopwatch.StartNew();while(end.Elapsed<TimeSpan.FromSeconds(seconds)){var s=await Snapshot(label);if(predicate(s.text,s.cols))return s;await Task.Delay(500,token);}throw new TimeoutException(label);}
  bool Prompt(string s)=>NativeDosText.HasPrompt(s);
  bool Completed(string s,string command,Func<string,bool> body)=>NativeDosText.Completed(s,command,body);
  async Task Type(string s){foreach(var c in s)await Command(1,(ushort)c);}
  try{
   // Parent proves actual SETUP source/closure before this new controller.
   if(!config.TryGetProperty("resume_existing",out var resume)||!resume.GetBoolean()){
   await client.ResetAsync(token);await Ready();await client.LoadExistingPrgAsync(home+"/START.PRG",cancellationToken:token);await Ready();var loaded=await Read(0x801,start.Length-2);if(!loaded.SequenceEqual(start.Skip(2)))throw new InvalidDataException("Generated START differs from native output");Save("START-cold-readback.bin",loaded);
   var sys=Encoding.ASCII.GetBytes("SYS2061\r");await Write(0x277,sys);if(!(await Read(0x277,sys.Length)).SequenceEqual(sys))throw new InvalidDataException("SYS body differs");await Write(0xc6,new[]{(byte)sys.Length});await client.ResumeAsync(token);
   }
   var end=Stopwatch.StartNew();while(true){var prefix=await Read(0x801,128);
    // KERNAL is deliberately still mapped during loader validation. The RAM
    // NMI vector becomes observable only after native takeover banks it out;
    // never interpret ROM bytes at the diagnostic address as runtime status.
    if(prefix.SequenceEqual(source.Skip(2).Take(128))&&(await Read(started,1))[0]==1&&BinaryPrimitives.ReadUInt16LittleEndian(await Read(0xfffa,2))==nmi){var state=await Read(diag,19);if(state[0]==0xe1)throw new InvalidDataException("Native bootstrap failure: "+Convert.ToHexString(state));if(state[0]==4){Save("native-RUN-diag.bin",state);Save("native-RUN-NMI.bin",BitConverter.GetBytes((ushort)nmi));break;}}if(end.Elapsed>TimeSpan.FromSeconds(180))throw new TimeoutException("Installed START to native RUN");await Task.Delay(100,token);}
   var initial=await WaitText("DOS-boot",(s,c)=>Prompt(s),150);if(!displayOnly){await Type("VER\r");await WaitText("VER",(s,c)=>Completed(s,"VER",t=>t.Contains("Version 3.30",StringComparison.OrdinalIgnoreCase)));
   await Type("DIR C:\r");await WaitText("DIR-C",(s,c)=>Completed(s,"DIR C:",t=>t.Contains("<DIR>")&&t.Contains("DOS")));}
   await Type("MODE CO40\r");await WaitText("MODE-40",(s,c)=>c==40&&Prompt(s));await Type("VER\r");await WaitText("VER-40",(s,c)=>c==40&&Completed(s,"VER",t=>t.Contains("Version 3.30",StringComparison.OrdinalIgnoreCase)));
   await Type("MODE CO80\r");await WaitText("MODE-80",(s,c)=>c==80&&Prompt(s));
   if(displayOnly){await Type("VER\r");await WaitText("VER-80",(s,c)=>c==80&&Completed(s,"VER",t=>t.Contains("Version 3.30",StringComparison.OrdinalIgnoreCase)));}
   File.WriteAllText(Path.Combine(output,"RESULT.json"),JsonSerializer.Serialize(new{status="passed",scope=displayOnly?"genuine_DOS_MODE40_VER_MODE80_VER_display_capture":"genuine_DOS_VER_DIR_C_MODE40_MODE80",display_state_captured=display,continued_existing=config.TryGetProperty("resume_existing",out var continued)&&continued.GetBoolean(),native_BIOS_keys=true,physical_CIA_claim=false,guest_disk_writes_requested=false,final_native_RUNNING=true,hardware_session_left_at_prompt=true,snapshots=serial}));return 0;
  }catch(Exception ex){File.WriteAllText(Path.Combine(output,"RESULT.json"),JsonSerializer.Serialize(new{status="failed",first_error=ex.ToString(),no_retry=true,no_reset_after_failure=true}));return 1;}
 }
}
