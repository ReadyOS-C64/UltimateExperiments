namespace ViceTasks.Ultimate;

public sealed partial class UltimateClient
{
    /// <summary>Opt-in bodyless memory writes, split at the firmware's128-byte
    /// inline limit. Existing WriteMemoryAsync behavior is unchanged.</summary>
    public async Task WriteMemoryInlineAsync(int address, byte[] data, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(data);
        if (address < 0 || address > 0xffff || data.Length > 0x10000 - address)
            throw new ArgumentOutOfRangeException(nameof(address));
        for (var offset = 0; offset < data.Length; offset += 128)
        {
            var hex = Convert.ToHexString(data.AsSpan(offset, Math.Min(128, data.Length - offset)));
            await PutAsync($"machine:writemem?address={address + offset:X4}&data={hex}", cancellationToken);
        }
    }

    /// <summary>Load an existing device file without a temporary HTTP upload.</summary>
    public Task LoadExistingPrgAsync(string path, bool run = false, CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(path);
        if (!path.StartsWith('/'))
            throw new ArgumentException("An absolute Ultimate file path is required.", nameof(path));
        return PutAsync($"runners:{(run ? "run_prg" : "load_prg")}?file={Uri.EscapeDataString(path)}", cancellationToken);
    }
    /// <summary>
    /// Publish one standard C64 PETSCII key at a time, and require its queue
    /// acknowledgement. Supports KERNAL programs and native applications that
    /// explicitly consume $0277/$C6. This does not emulate the CIA matrix.
    /// Existing keyboard methods retain their original behavior.
    /// </summary>
    public async Task WriteKeySequenceCheckedAsync(
        IReadOnlyList<byte> keyCodes,
        TimeSpan keyTimeout,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(keyCodes);
        if (keyTimeout <= TimeSpan.Zero || keyTimeout > TimeSpan.FromMinutes(1))
            throw new ArgumentOutOfRangeException(nameof(keyTimeout));

        for (var i = 0; i < keyCodes.Count; i++)
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            deadline.CancelAfter(keyTimeout);
            try
            {
                await WaitEmptyCheckedAsync(deadline.Token);
                await WriteMemoryInlineAsync(0x00C5, [0x00], deadline.Token);
                await WriteMemoryInlineAsync(0x0277, [keyCodes[i]], deadline.Token);
                await WriteMemoryInlineAsync(0x00C6, [0x01], deadline.Token);
                await WaitEmptyCheckedAsync(deadline.Token);
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                // A failed/ambiguous write is never repeated or followed by
                // another key. Preserve application state for diagnosis.
                throw new TimeoutException($"C64 keyboard queue did not acknowledge key {i} (0x{keyCodes[i]:X2}); no retry was sent.");
            }
        }
    }

    private async Task WaitEmptyCheckedAsync(CancellationToken cancellationToken)
    {
        while (true)
        {
            var count = await ReadMemoryAsync(0x00C6, 1, cancellationToken);
            if (count.Length != 1 || count[0] > 10)
                throw new InvalidDataException("C64 keyboard queue has an invalid count; no input was published.");
            if (count[0] == 0)
                return;
            await Task.Delay(TimeSpan.FromMilliseconds(20), cancellationToken);
        }
    }
}
