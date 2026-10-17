namespace ViceTasks.Ultimate;

public sealed partial class UltimateClient
{
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
                await WriteMemoryAsync(0x00C5, [0x00], deadline.Token);
                await WriteMemoryAsync(0x0277, [keyCodes[i]], deadline.Token);
                await WriteMemoryAsync(0x00C6, [0x01], deadline.Token);
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
