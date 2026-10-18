program Ripple;
{$G-}
uses Dos;
const p:array[0..7] of byte=(1,5,4,12,14,15,11,9);
var x,y,d,e:integer; r:Registers;
begin
  r.ax:=1; Intr($10,r);
  for y:=1 to 24 do
    for x:=0 to 39 do begin
      d:=((x-11)*(x-11)+(y-12)*(y-12)) div 6;
      e:=((x-28)*(x-28)+(y-12)*(y-12)) div 6;
      Mem[$B800:2*(y*40+x)]:=219;
      Mem[$B800:2*(y*40+x)+1]:=p[(d xor e) mod 8];
    end;
  Write('RIPPLE - press a key');
  r.ax:=0; Intr($16,r);
  r.ax:=3; Intr($10,r)
end.
