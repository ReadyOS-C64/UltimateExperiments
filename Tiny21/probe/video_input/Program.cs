using System.Diagnostics;
using ViceTasks.Ultimate;

using var ultimate = new UltimateClient(new UltimateClientOptions { Host = args[0] });
var timeout = TimeSpan.FromSeconds(3);
var typingClock = Stopwatch.StartNew();
var time = 0;
foreach (var (character, index) in args[1].ToUpperInvariant().Select((value, index) => (value, index)))
{
    var remaining = TimeSpan.FromMilliseconds(time) - typingClock.Elapsed;
    if (remaining > TimeSpan.Zero)
        await Task.Delay(remaining);
    await ultimate.WriteKeySequenceCheckedAsync([(byte)character], timeout);
    time += character == ' ' ? 195 : 142 + index % 5 * 11;
}

// The VIC reading phase acknowledges RETURN. RAM polling here can race inference.
var untilReturn = TimeSpan.FromMilliseconds(time) - typingClock.Elapsed;
if (untilReturn > TimeSpan.Zero)
    await Task.Delay(untilReturn);
await ultimate.WriteMemoryInlineAsync(0x00C5, [0]);
await ultimate.WriteMemoryInlineAsync(0x0277, [13]);
await ultimate.WriteMemoryInlineAsync(0x00C6, [1]);
