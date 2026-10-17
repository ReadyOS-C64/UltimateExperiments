using System.Buffers.Binary;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

namespace ViceTasks.Ultimate;

public sealed class UltimateClientOptions
{
    public string Host { get; init; } = "10.0.0.79";
    public string? Password { get; init; }
    public string FtpUser { get; init; } = "anonymous";
    public string FtpPassword { get; init; } = "anonymous@";
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(10);
}

public sealed partial class UltimateClient : IDisposable
{
    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly string _host;
    private readonly string _ftpUser;
    private readonly string _ftpPassword;

    public UltimateClient(UltimateClientOptions options)
    {
        _host = options.Host.TrimEnd('/');
        _ftpUser = options.FtpUser;
        _ftpPassword = options.FtpPassword;
        _baseUrl = $"http://{_host}/v1";
        _http = new HttpClient { Timeout = options.Timeout };
        if (!string.IsNullOrWhiteSpace(options.Password))
        {
            _http.DefaultRequestHeaders.Add("X-Password", options.Password);
        }
    }

    public async Task<JsonDocument> GetInfoAsync(CancellationToken cancellationToken = default)
        => await GetJsonAsync("info", cancellationToken);

    public async Task<JsonDocument> GetVersionAsync(CancellationToken cancellationToken = default)
        => await GetJsonAsync("version", cancellationToken);

    public async Task<JsonDocument> GetDrivesAsync(CancellationToken cancellationToken = default)
        => await GetJsonAsync("drives", cancellationToken);

    public async Task ResetAsync(CancellationToken cancellationToken = default)
        => await PutAsync("machine:reset", cancellationToken);

    public async Task PauseAsync(CancellationToken cancellationToken = default)
        => await PutAsync("machine:pause", cancellationToken);

    public async Task ResumeAsync(CancellationToken cancellationToken = default)
        => await PutAsync("machine:resume", cancellationToken);

    public async Task MenuButtonAsync(CancellationToken cancellationToken = default)
        => await PutAsync("machine:menu_button", cancellationToken);

    public async Task LoadPrgAsync(byte[] prg, CancellationToken cancellationToken = default)
        => await PostBytesAsync("runners:load_prg", prg, "application/octet-stream", cancellationToken);

    public async Task RunPrgAsync(byte[] prg, CancellationToken cancellationToken = default)
        => await PostBytesAsync("runners:run_prg", prg, "application/octet-stream", cancellationToken);

    public async Task RunCrtAsync(byte[] crt, CancellationToken cancellationToken = default)
        => await PostBytesAsync("runners:run_crt", crt, "application/octet-stream", cancellationToken);

    public async Task MountDiskImageAsync(
        string drive,
        string diskImagePath,
        string mode = "readwrite",
        string? type = null,
        CancellationToken cancellationToken = default)
    {
        using var form = new MultipartFormDataContent();
        await using var stream = File.OpenRead(diskImagePath);
        using var content = new StreamContent(stream);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/octet-stream");
        form.Add(content, "file", Path.GetFileName(diskImagePath));
        form.Add(new StringContent(mode), "mode");
        form.Add(new StringContent(type ?? Path.GetExtension(diskImagePath).TrimStart('.').ToLowerInvariant()), "type");

        using var response = await _http.PostAsync(Url($"drives/{drive}:mount"), form, cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
    }

    public async Task UploadFileToUsbAsync(string localPath, string remotePath, CancellationToken cancellationToken = default)
    {
        var normalizedRemote = remotePath.TrimStart('/');
        var psi = new ProcessStartInfo
        {
            FileName = "/usr/bin/curl",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        psi.ArgumentList.Add("--fail");
        psi.ArgumentList.Add("--silent");
        psi.ArgumentList.Add("--show-error");
        psi.ArgumentList.Add("--ftp-create-dirs");
        psi.ArgumentList.Add("-T");
        psi.ArgumentList.Add(localPath);
        psi.ArgumentList.Add($"ftp://{_host}/{normalizedRemote}");
        psi.ArgumentList.Add("--user");
        psi.ArgumentList.Add($"{_ftpUser}:{_ftpPassword}");

        using var proc = Process.Start(psi) ?? throw new InvalidOperationException("failed to start curl for Ultimate FTP upload");
        var stdoutTask = proc.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = proc.StandardError.ReadToEndAsync(cancellationToken);
        await proc.WaitForExitAsync(cancellationToken);
        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        if (proc.ExitCode != 0)
        {
            throw new HttpRequestException($"Ultimate FTP upload failed with exit code {proc.ExitCode}: {stderr}{stdout}");
        }
    }

    public async Task MountExistingDiskImageAsync(
        string drive,
        string remoteImagePath,
        string mode = "unlinked",
        string? type = null,
        CancellationToken cancellationToken = default)
    {
        var normalizedImage = remoteImagePath.Trim();
        if (!normalizedImage.StartsWith("/", StringComparison.Ordinal))
        {
            normalizedImage = "/" + normalizedImage.TrimStart('/');
        }
        var query = new Dictionary<string, string?>
        {
            ["image"] = normalizedImage,
            ["type"] = string.IsNullOrWhiteSpace(type) ? null : type,
            ["mode"] = mode,
        };
        var queryText = string.Join("&", query
            .Where(kv => !string.IsNullOrWhiteSpace(kv.Value))
            .Select(kv => $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value!)}"));
        await PutAsync($"drives/{drive}:mount?{queryText}", cancellationToken);
    }

    public async Task ConfigureDriveAsync(
        string drive,
        int busId,
        string driveType,
        bool enabled = true,
        CancellationToken cancellationToken = default)
    {
        var driveName = drive.Trim().ToLowerInvariant() switch
        {
            "a" or "drivea" or "drive_a" => "Drive A Settings",
            "b" or "driveb" or "drive_b" => "Drive B Settings",
            _ => throw new ArgumentException("Ultimate drive must be 'a' or 'b'", nameof(drive)),
        };

        var payload = new Dictionary<string, Dictionary<string, object?>>
        {
            [driveName] = new()
            {
                ["Drive"] = enabled ? "Enabled" : "Disabled",
                ["Drive Type"] = driveType,
                ["Drive Bus ID"] = busId,
            },
        };

        var json = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload));
        using var content = new ByteArrayContent(json);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
        using var response = await _http.PostAsync(Url("configs"), content, cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
    }

    public async Task SetTurboSpeedAsync(int mhz, CancellationToken cancellationToken = default)
    {
        if (!UltimateSpeed.IsValid(mhz))
        {
            throw new ArgumentOutOfRangeException(nameof(mhz), $"Ultimate CPU speed must be one of: {string.Join(", ", UltimateSpeed.ValidMhz)}");
        }

        var payload = new Dictionary<string, Dictionary<string, object?>>
        {
            ["U64 Specific Settings"] = new()
            {
                ["Turbo Control"] = mhz <= 1 ? "Off" : "Manual",
                ["CPU Speed"] = UltimateSpeed.FormatMhz(mhz),
            },
        };

        var json = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload));
        using var content = new ByteArrayContent(json);
        content.Headers.ContentType = new MediaTypeHeaderValue("application/json");
        using var response = await _http.PostAsync(Url("configs"), content, cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
    }

    public async Task<byte[]> ReadMemoryAsync(int address, int length, CancellationToken cancellationToken = default)
    {
        if (address is < 0 or > 0xFFFF)
        {
            throw new ArgumentOutOfRangeException(nameof(address), "address must be 0x0000..0xFFFF");
        }

        if (length < 0 || address + length > 0x10000)
        {
            throw new ArgumentOutOfRangeException(nameof(length), "memory read must stay within C64 address space");
        }

        using var response = await _http.GetAsync(Url($"machine:readmem?address={address:X}&length={length}"), cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
        return await response.Content.ReadAsByteArrayAsync(cancellationToken);
    }

    public async Task WriteMemoryAsync(int address, byte[] data, CancellationToken cancellationToken = default)
    {
        if (address is < 0 or > 0xFFFF)
        {
            throw new ArgumentOutOfRangeException(nameof(address), "address must be 0x0000..0xFFFF");
        }

        if (data.Length == 0)
        {
            return;
        }

        if (address + data.Length > 0x10000)
        {
            throw new ArgumentOutOfRangeException(nameof(data), "memory write must stay within C64 address space");
        }

        var hex = Convert.ToHexString(data).ToLowerInvariant();
        await PutAsync($"machine:writemem?address={address:X4}&data={hex}", cancellationToken);
    }

    public async Task WriteKeyboardBufferAsync(IReadOnlyList<byte> keyCodes, TimeSpan interChunkDelay, CancellationToken cancellationToken = default)
    {
        foreach (var chunk in keyCodes.Chunk(10))
        {
            await WaitKeyboardBufferEmptyAsync(cancellationToken);
            await WriteMemoryAsync(0x00C5, [0x00, 0x00], cancellationToken);
            await WriteMemoryAsync(0x0277, chunk, cancellationToken);
            await WriteMemoryAsync(0x00C6, [(byte)chunk.Length], cancellationToken);
            await WaitKeyboardBufferEmptyAsync(cancellationToken);

            if (interChunkDelay > TimeSpan.Zero)
            {
                await Task.Delay(interChunkDelay, cancellationToken);
            }
        }
    }

    private async Task WaitKeyboardBufferEmptyAsync(CancellationToken cancellationToken)
    {
        for (var attempt = 0; attempt < 200; attempt++)
        {
            var count = await ReadMemoryAsync(0x00C6, 1, cancellationToken);
            if (count.Length > 0 && count[0] == 0)
            {
                return;
            }

            await Task.Delay(TimeSpan.FromMilliseconds(20), cancellationToken);
        }
    }

    public async Task WriteKeySequenceAsync(IReadOnlyList<byte> keyCodes, TimeSpan interKeyDelay, CancellationToken cancellationToken = default)
    {
        foreach (var keyCode in keyCodes)
        {
            await WriteKeyboardBufferAsync([keyCode], TimeSpan.Zero, cancellationToken);

            if (interKeyDelay > TimeSpan.Zero)
            {
                await Task.Delay(interKeyDelay, cancellationToken);
            }
        }
    }

    public async Task TypeTextAsync(string text, TimeSpan interChunkDelay, CancellationToken cancellationToken = default)
    {
        var bytes = text
            .Select(ch => ch == '\n' ? (byte)0x0D : ch == '\r' ? (byte)0x0D : (byte)char.ToUpperInvariant(ch))
            .ToArray();
        await WriteKeyboardBufferAsync(bytes, interChunkDelay, cancellationToken);
    }

    public async Task<ScreenSnapshot> ReadScreenAsync(CancellationToken cancellationToken = default)
    {
        var codes = await ReadMemoryAsync(C64Screen.ScreenAddress, C64Screen.ScreenLength, cancellationToken);
        return C64Screen.Decode(codes);
    }

    public async Task StartStreamAsync(string streamName, IPAddress targetIp, int port, CancellationToken cancellationToken = default)
        => await PutAsync($"streams/{streamName}:start?ip={targetIp}:{port}", cancellationToken);

    public async Task StopStreamAsync(string streamName, CancellationToken cancellationToken = default)
        => await PutAsync($"streams/{streamName}:stop", cancellationToken);

    public async Task<Image<Rgba32>> CaptureVideoFrameAsync(
        IPAddress? targetIp = null,
        int port = 11000,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        var localIp = targetIp ?? LocalNetwork.FindLikelyLocalIPv4();
        using var receiver = new UltimateVideoFrameReceiver(port, timeout ?? TimeSpan.FromSeconds(4));
        await StartStreamAsync("video", localIp, port, cancellationToken);
        try
        {
            return await receiver.CaptureImageAsync(cancellationToken);
        }
        finally
        {
            try
            {
                await StopStreamAsync("video", cancellationToken);
            }
            catch
            {
                // Capture should still be useful when stopping the stream fails.
            }
        }
    }

    private async Task<JsonDocument> GetJsonAsync(string path, CancellationToken cancellationToken)
    {
        using var response = await _http.GetAsync(Url(path), cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
    }

    private async Task PutAsync(string path, CancellationToken cancellationToken)
    {
        using var response = await _http.PutAsync(Url(path), content: null, cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
    }

    private async Task PostBytesAsync(string path, byte[] bytes, string contentType, CancellationToken cancellationToken)
    {
        using var content = new ByteArrayContent(bytes);
        content.Headers.ContentType = new MediaTypeHeaderValue(contentType);
        using var response = await _http.PostAsync(Url(path), content, cancellationToken);
        await EnsureOkAsync(response, cancellationToken);
    }

    private string Url(string path) => $"{_baseUrl}/{path}";

    private static async Task EnsureOkAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode)
        {
            return;
        }

        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        var reason = response.StatusCode == HttpStatusCode.Forbidden
            ? "access denied; check the Ultimate network password"
            : string.IsNullOrWhiteSpace(body) ? response.ReasonPhrase : body;
        throw new HttpRequestException($"Ultimate API request failed ({(int)response.StatusCode} {response.StatusCode}): {reason}");
    }

    public void Dispose() => _http.Dispose();
}

public sealed record ScreenSnapshot(byte[] Codes, string[] Lines);

public static class C64Screen
{
    public const int ScreenAddress = 0x0400;
    public const int ScreenLength = 1000;
    public const int Width = 40;
    public const int Height = 25;

    public static ScreenSnapshot Decode(byte[] codes)
    {
        var lines = new string[Height];
        for (var y = 0; y < Height; y++)
        {
            var chars = new char[Width];
            for (var x = 0; x < Width; x++)
            {
                var idx = y * Width + x;
                chars[x] = idx < codes.Length ? ScreenCodeToAscii(codes[idx]) : ' ';
            }
            lines[y] = new string(chars);
        }

        return new ScreenSnapshot(codes, lines);
    }

    public static bool Contains(ScreenSnapshot snapshot, string needle)
        => string.Join("\n", snapshot.Lines).Contains(needle, StringComparison.OrdinalIgnoreCase);

    public static char ScreenCodeToAscii(byte b)
    {
        if (b is >= 1 and <= 26)
        {
            return (char)(b - 1 + 'A');
        }

        if (b is >= 48 and <= 57)
        {
            return (char)(b - 48 + '0');
        }

        return b switch
        {
            0 => '@',
            27 => '[',
            29 => ']',
            32 => ' ',
            33 => '!',
            34 => '"',
            35 => '#',
            36 => '$',
            37 => '%',
            38 => '&',
            39 => '\'',
            40 => '(',
            41 => ')',
            42 => '*',
            43 => '+',
            44 => ',',
            45 => '-',
            46 => '.',
            47 => '/',
            58 => ':',
            59 => ';',
            60 => '<',
            61 => '=',
            62 => '>',
            63 => '?',
            100 => '_',
            160 => '#',
            _ => '.',
        };
    }
}

public sealed class UltimateVideoFrameReceiver : IDisposable
{
    private const ushort EndOfFrame = 1 << 15;
    private const int LineNumberOffset = 4;
    private const int HeaderLength = 12;
    private const int ImageWidth = 384;
    private const int BytesPerRow = ImageWidth / 2;

    private static readonly Rgba32[] Palette =
    [
        new(0x00, 0x00, 0x00),
        new(0xEF, 0xEF, 0xEF),
        new(0x8D, 0x2F, 0x34),
        new(0x6A, 0xD4, 0xCD),
        new(0x98, 0x35, 0xA4),
        new(0x4C, 0xB4, 0x42),
        new(0x2C, 0x29, 0xB1),
        new(0xEF, 0xEF, 0x5D),
        new(0x98, 0x4E, 0x20),
        new(0x5B, 0x38, 0x00),
        new(0xD1, 0x67, 0x6D),
        new(0x4A, 0x4A, 0x4A),
        new(0x7B, 0x7B, 0x7B),
        new(0x9F, 0xEF, 0x93),
        new(0x6D, 0x6A, 0xEF),
        new(0xB2, 0xB2, 0xB2),
    ];

    private readonly UdpClient _udp;
    private readonly TimeSpan _timeout;

    public UltimateVideoFrameReceiver(int port = 11000, TimeSpan? timeout = null)
    {
        _timeout = timeout ?? TimeSpan.FromSeconds(4);
        _udp = new UdpClient(AddressFamily.InterNetwork);
        _udp.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        _udp.Client.Bind(new IPEndPoint(IPAddress.Any, port));
        _udp.JoinMulticastGroup(IPAddress.Parse("239.0.1.64"));
    }

    public async Task<Image<Rgba32>> CaptureImageAsync(CancellationToken cancellationToken = default)
    {
        var frame = await CaptureFrameBytesAsync(cancellationToken);
        var rows = Math.Max(1, frame.Length / BytesPerRow);
        var img = new Image<Rgba32>(ImageWidth, rows);
        var i = 0;
        for (var y = 0; y < rows; y++)
        {
            for (var x = 0; x < BytesPerRow && i < frame.Length; x++)
            {
                var value = frame[i++];
                img[x * 2, y] = Palette[value & 0x0F];
                img[x * 2 + 1, y] = Palette[(value >> 4) & 0x0F];
            }
        }

        return img;
    }

    private async Task<byte[]> CaptureFrameBytesAsync(CancellationToken cancellationToken)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        cts.CancelAfter(_timeout);

        while (true)
        {
            var datagram = await _udp.ReceiveAsync(cts.Token);
            if (IsEndOfFrame(datagram.Buffer))
            {
                break;
            }
        }

        var frame = new List<byte>(384 * 272 / 2);
        while (true)
        {
            var datagram = await _udp.ReceiveAsync(cts.Token);
            var buffer = datagram.Buffer;
            if (buffer.Length >= HeaderLength)
            {
                frame.AddRange(buffer.AsSpan(HeaderLength).ToArray());
                if (IsEndOfFrame(buffer))
                {
                    break;
                }
            }
        }

        return frame.ToArray();
    }

    private static bool IsEndOfFrame(byte[] buffer)
    {
        if (buffer.Length < HeaderLength)
        {
            return false;
        }

        var line = BinaryPrimitives.ReadUInt16LittleEndian(buffer.AsSpan(LineNumberOffset, 2));
        return (line & EndOfFrame) != 0;
    }

    public void Dispose() => _udp.Dispose();
}

public static class LocalNetwork
{
    public static IPAddress FindLikelyLocalIPv4()
    {
        foreach (var networkInterface in NetworkInterface.GetAllNetworkInterfaces())
        {
            if (networkInterface.OperationalStatus != OperationalStatus.Up)
            {
                continue;
            }

            var props = networkInterface.GetIPProperties();
            foreach (var address in props.UnicastAddresses)
            {
                if (address.Address.AddressFamily == AddressFamily.InterNetwork &&
                    !IPAddress.IsLoopback(address.Address))
                {
                    return address.Address;
                }
            }
        }

        throw new InvalidOperationException("could not determine local IPv4 address for Ultimate stream target");
    }
}

public static class HexDump
{
    public static string Format(int startAddress, byte[] data)
    {
        var sb = new StringBuilder();
        for (var off = 0; off < data.Length; off += 16)
        {
            var len = Math.Min(16, data.Length - off);
            sb.Append('$');
            sb.Append((startAddress + off).ToString("X4", CultureInfo.InvariantCulture));
            sb.Append(':');
            for (var i = 0; i < len; i++)
            {
                sb.Append(' ');
                sb.Append(data[off + i].ToString("X2", CultureInfo.InvariantCulture));
            }
            sb.AppendLine();
        }

        return sb.ToString();
    }
}

public static class UltimateSpeed
{
    public static readonly int[] ValidMhz = [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20, 24, 32, 40, 48, 64];

    public static bool IsValid(int mhz) => ValidMhz.Contains(mhz);

    public static string FormatMhz(int mhz)
        => mhz < 10 ? $" {mhz}" : mhz.ToString(CultureInfo.InvariantCulture);
}
