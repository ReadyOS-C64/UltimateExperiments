using System.Text.RegularExpressions;

// Read-only observation rules for default DOS prompts and PROMPT $P$G.
internal static class NativeDosText
{
    const string PromptPrefix = @"(?:[A-Z]:\\[^\r\n>]*|[A-Z])>";

    internal static bool HasPrompt(string text) =>
        Regex.IsMatch(text, "(?im)^" + PromptPrefix + @"[^\S\r\n]*$");

    internal static bool Completed(string text, string command, Func<string, bool> body)
    {
        var echoes = Regex.Matches(text,
            "(?im)^" + PromptPrefix + Regex.Escape(command) + @"[ \r]*\n");
        if (echoes.Count == 0)
            return false;
        var last = echoes[^1];
        var following = text[(last.Index + last.Length)..];
        return body(following) && HasPrompt(following);
    }
}
