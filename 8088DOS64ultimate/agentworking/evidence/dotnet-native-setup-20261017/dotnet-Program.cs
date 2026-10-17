using System.Security.Cryptography;
using System.Text.Json;
using ViceTasks.Ultimate;

if(args.Length!=1)throw new ArgumentException("Supply a source-bound JSON run configuration.");
using var configuration=JsonDocument.Parse(File.ReadAllBytes(args[0]));var config=configuration.RootElement;
var output=config.GetProperty("output").GetString()!;Directory.CreateDirectory(output);
var home=config.GetProperty("home").GetString()!;var host=config.GetProperty("host").GetString()!;
using var limit=new CancellationTokenSource(TimeSpan.FromSeconds(480));
using var client=new UltimateClient(new(){Host=host});var token=limit.Token;var serial=0;
var events=new List<object>();
void Save(string name,object data)=>File.WriteAllText(Path.Combine(output,name),JsonSerializer.Serialize(data,new JsonSerializerOptions{WriteIndented=true}));
async Task<ScreenSnapshot> Screen(string label){var s=C64MixedCaseScreen.Decode(await client.ReadMemoryAsync(0x400,1000,token));var n=++serial;File.WriteAllBytes(Path.Combine(output,$"{n:D4}-{label}.bin"),s.Codes);File.WriteAllLines(Path.Combine(output,$"{n:D4}-{label}.txt"),s.Lines);return s;}
async Task<ScreenSnapshot> Wait(Func<ScreenSnapshot,bool> predicate,string label,int seconds=30){var end=DateTime.UtcNow.AddSeconds(seconds);while(DateTime.UtcNow<end){var s=await Screen(label);if(C64Screen.Contains(s,"SETUP STOPPED")){File.WriteAllLines(Path.Combine(output,"FIRST_TARGET_ERROR.txt"),s.Lines);throw new InvalidOperationException("Native SETUP stopped; see FIRST_TARGET_ERROR.txt");}if(predicate(s))return s;await Task.Delay(100,token);}throw new TimeoutException(label);}
async Task Key(byte k){await client.WriteKeySequenceCheckedAsync(new[]{k},TimeSpan.FromSeconds(4),token);events.Add(new{kind="checked_standard_buffer_key",petscii=k});Save("events.json",events);}
bool Settled(ScreenSnapshot s)=>!C64Screen.Contains(s,"Reading folder...");
int Selected(ScreenSnapshot s){for(var i=0;i<12;i++)if(s.Lines[5+i][0]=='>')return i;throw new InvalidDataException("No selected native browser row");}
string Item(ScreenSnapshot s,int i)=>Uri.UnescapeDataString(s.Lines[5+i][2..].TrimEnd());
async Task Select(string name){
 for(var page=0;page<128;page++){
  var s=await Wait(Settled,"browser-ready");var target=Enumerable.Range(0,12).FirstOrDefault(i=>Item(s,i).Equals(name,StringComparison.OrdinalIgnoreCase),-1);
  if(target>=0){
   var selected=Selected(s);
   while(selected!=target){var next=selected+(selected<target?1:-1);await Key(selected<target?(byte)17:(byte)145);s=await Wait(x=>Settled(x)&&Selected(x)==next,"cursor");selected=next;}
   var previous=s.Lines[1]+s.Lines[3];await Key(13);
   await Wait(x=>Settled(x)&&(x.Lines[1]+x.Lines[3]!=previous),"selected-entry");events.Add(new{kind="native_browser_choice",name});return;
  }
  var old=string.Join("\n",s.Lines.Skip(5).Take(12));await Key(135);
  await Wait(x=>Settled(x)&&string.Join("\n",x.Lines.Skip(5).Take(12))!=old,"next-page");
 }
 throw new InvalidDataException("Entry absent after128pages: "+name);
}
if(config.TryGetProperty("mode",out var mode)&&mode.GetString()=="capture"){
 await client.PauseAsync(token);
 try { var a=await client.ReadMemoryAsync(0,32768,token);var b=await client.ReadMemoryAsync(32768,32768,token);File.WriteAllBytes(Path.Combine(output,"RAM.bin"),a.Concat(b).ToArray());await Screen("native-terminal");Save("RESULT.json",new{status="passed",scope="read_only_coherent_native_terminal_capture",bytes=a.Length+b.Length});}
 finally{await client.ResumeAsync(token);}
 return 0;
}
try{
 await Wait(x=>C64Screen.Contains(x,"Choose the DOS64 home folder")&&Settled(x),"home-menu");
 foreach(var part in home.Split('/',StringSplitOptions.RemoveEmptyEntries))await Select(part);
 await Key(133);await Wait(x=>C64Screen.Contains(x,"Choose DOS disk 1")&&Settled(x),"disk1-menu");
 foreach(var name in new[]{"DOS1.IMG","DOS2.IMG","DOS3.IMG"})await Select(name);
 await Wait(x=>C64Screen.Contains(x,"Import an existing C image?")&&Settled(x),"import-menu");await Key(133);
 await Wait(x=>C64Screen.Contains(x,"Choose C drive size"),"size-menu");await Key(13);
 await Wait(x=>C64Screen.Contains(x,"Review installation choices"),"review");await Key(13);
 var final=await Wait(x=>C64Screen.Contains(x,"INSTALL COMPLETE"),"install-progress",300);
 Save("RESULT.json",new{status="passed",scope="real_native_SETUP_driven_by_dotnet_standard_keyboard_buffer",home,physical_CIA_input=false,complete_caption=true,keys=events.Count(x=>x.ToString()!.Contains("petscii")),screens=serial});
 Console.WriteLine("Actual native SETUP completed through .NET keyboard automation.");return 0;
}catch(Exception e){Save("RESULT.json",new{status="failed",first_error=e.ToString(),no_retry=true,no_reset=true,screens=serial});Console.Error.WriteLine(e);return 1;}
