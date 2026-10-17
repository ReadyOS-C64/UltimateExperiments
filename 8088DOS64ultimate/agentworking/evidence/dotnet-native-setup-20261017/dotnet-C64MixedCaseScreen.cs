namespace ViceTasks.Ultimate;

/// <summary>Opt-in decoder for the C64 mixed-case character ROM ($D018=$16).
/// The established C64Screen decoder and existing plan captures are unchanged.</summary>
public static class C64MixedCaseScreen
{
    public static ScreenSnapshot Decode(byte[] codes)
    {
        var lines = new string[C64Screen.Height];
        for (var y = 0; y < C64Screen.Height; y++)
        {
            var chars = new char[C64Screen.Width];
            for (var x = 0; x < chars.Length; x++)
            {
                var index = y * chars.Length + x;
                var code = index < codes.Length ? codes[index] & 0x7f : 32;
                chars[x] = code switch
                {
                    >= 1 and <= 26 => (char)(code + 96),
                    0 => '@',
                    27 => '[',
                    29 => ']',
                    >= 32 and <= 90 => (char)code,
                    _ => '.',
                };
            }
            lines[y] = new string(chars);
        }
        return new ScreenSnapshot(codes, lines);
    }
}
