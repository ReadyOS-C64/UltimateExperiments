const CHECKPOINT_SHA = "4b603237070ad9084433537bf8d6c7470d0fc583e6a4f1f03c00cd17264e7095";
const MODEL_SHA = "ba89630a6bb1fd2d385e6daeae6bbc27a919996703e12e4beb4ab06136f61a1b";
const PRG_SHA = "f288bc9d5279cc3e4b32a5294f768586f2555a0a95b9b8534cfc905243b0a860";
const CHECKPOINT = "https://raw.githubusercontent.com/WollyMonjac/Tiny-2.1/1d5cf54677addf188a090ca1c91acb3d02989a1d/TINY.BIN";
const encoder = new TextEncoder();

async function checkHash(bytes, expected) {
    const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    if (Array.from(hash, byte => byte.toString(16).padStart(2, "0")).join("") !== expected) {
        throw new Error("A downloaded file failed its integrity check.");
    }
    return hash;
}

function roundEven(value) {
    const floor = Math.floor(value);
    const fraction = value - floor;
    return floor + Number(fraction > 0.5 || (fraction === 0.5 && (floor & 1)));
}

function pack(row, mode, target, offset) {
    if (mode === 0) {
        target.set(row, offset);
        return;
    }
    const pairs = mode === 4 ? 2 : 1;
    for (let bit = 8 - pairs; bit >= 0; bit -= pairs) {
        for (let first = 0; first < row.length; first += mode) {
            let mask = 0;
            for (let lane = 0; lane < mode; lane++) {
                for (let plane = 0; plane < pairs; plane++) {
                    mask |= ((row[first + lane] >>> (bit + plane)) & 1) << (lane + plane * mode);
                }
            }
            target[offset++] = mask;
        }
    }
}

export async function convertModel(input) {
    const digest = await checkHash(input, CHECKPOINT_SHA);
    const source = new DataView(input);
    const output = new Uint8Array(380995);
    const header = new DataView(output.buffer);
    const gains = [];
    let from = 12;
    let to = 4096;
    let directory = 64;
    function matrix(rows, columns, mode = 0) {
        header.setUint32(directory, to, true);
        header.setUint16(directory + 4, rows, true);
        header.setUint16(directory + 6, columns, true);
        directory += 8;
        for (let first = 0; first < rows; first += 16) {
            const count = Math.min(16, rows - first);
            let scales = to + count * columns;
            for (let row = 0; row < count; row++) {
                const scale = roundEven(source.getFloat32(from, true) * 0x1000000);
                output[scales++] = scale & 255;
                output[scales++] = (scale >>> 8) & 255;
                output[scales++] = scale >>> 16;
                pack(new Uint8Array(input, from + 4, columns), mode, output, to);
                from += 4 + columns;
                to += columns;
            }
            to = scales;
        }
    }
    function gain() {
        for (let lane = 0; lane < 96; lane++) {
            gains.push(roundEven(source.getFloat32(from, true) * 4096));
            from += 4;
        }
    }
    matrix(97, 96);
    matrix(128, 96);
    for (let layer = 0; layer < 4; layer++) {
        gain();
        for (let projection = 0; projection < 3; projection++) matrix(96, 96, 8);
        matrix(96, 96, 4);
        gain();
        matrix(256, 96, 8);
        matrix(96, 256);
    }
    gain();
    output.set(encoder.encode("T64M"));
    output.set([3, 96, 4, 4], 4);
    header.setUint16(8, 256, true);
    header.setUint16(10, (directory - 64) / 8, true);
    header.setUint32(12, output.length, true);
    header.setUint32(16, to, true);
    output.set(digest, 20);
    for (const value of gains) {
        header.setInt16(to, value, true);
        to += 2;
    }
    await checkHash(output, MODEL_SHA);
    return output;
}

function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
}

function zip(entries) {
    const files = [];
    const directory = [];
    let start = 0;
    let directorySize = 0;
    for (const [filename, bytes] of entries) {
        const name = encoder.encode(filename);
        const crc = crc32(bytes);
        const local = new DataView(new ArrayBuffer(30));
        local.setUint32(0, 0x04034b50, true);
        local.setUint16(4, 20, true);
        local.setUint16(12, 0x5d6f, true);
        local.setUint32(14, crc, true);
        local.setUint32(18, bytes.length, true);
        local.setUint32(22, bytes.length, true);
        local.setUint16(26, name.length, true);
        const central = new DataView(new ArrayBuffer(46));
        central.setUint32(0, 0x02014b50, true);
        central.setUint16(4, 20, true);
        new Uint8Array(central.buffer).set(new Uint8Array(local.buffer, 4, 26), 6);
        central.setUint32(42, start, true);
        files.push(local.buffer, name, bytes);
        directory.push(central.buffer, name);
        start += 30 + name.length + bytes.length;
        directorySize += 46 + name.length;
    }
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true);
    end.setUint16(8, entries.length, true);
    end.setUint16(10, entries.length, true);
    end.setUint32(12, directorySize, true);
    end.setUint32(16, start, true);
    return new Blob([...files, ...directory, end.buffer], {type: "application/zip"});
}

async function download(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`A required file could not be downloaded (HTTP ${response.status}).`);
    return response;
}

export async function prepareRelease(base = new URL(".", import.meta.url)) {
    const [checkpoint, program, guide, license] = await Promise.all([
        download(CHECKPOINT).then(response => response.arrayBuffer()),
        download(new URL("install/PROBE.PRG", base)).then(response => response.arrayBuffer()),
        download(new URL("DOWNLOAD.md", base)).then(response => response.text()),
        download(new URL("install/LICENSE", base)).then(response => response.arrayBuffer()),
    ]);
    await checkHash(program, PRG_SHA);
    const model = await convertModel(checkpoint);
    const startOfSetup = guide.indexOf("## Set up the Ultimate");
    if (startOfSetup === -1) throw new Error("The setup guide could not be read.");
    const setup = guide.slice(startOfSetup).replace(
        "(FUTURE.md)", "(https://readyos-c64.github.io/UltimateExperiments/tiny21/FUTURE.html)",
    );
    const readme = "# Tiny 2.1 v0.6 for the C64 Ultimate\n\n" +
        "**Required hardware: a C64 Ultimate with 64 MHz turbo support and a 16 MB REU.**\n\n" +
        "This ZIP contains PROBE.PRG and the matching MODEL.BIN.\n\n" + setup;
    return zip([["PROBE.PRG", new Uint8Array(program)], ["MODEL.BIN", model],
                ["README.md", encoder.encode(readme)], ["LICENSE", new Uint8Array(license)]]);
}

if (typeof document !== "undefined") {
    const button = document.querySelector("#tiny21-download");
    const status = document.querySelector("#tiny21-download-status");
    button.disabled = false;
    document.querySelector("#tiny21-github-download").hidden = true;
    status.textContent = "";
    button.addEventListener("click", async () => {
        button.disabled = true;
        status.textContent = "Preparing your ZIP…";
        try {
            const url = URL.createObjectURL(await prepareRelease());
            const link = document.createElement("a");
            link.href = url;
            link.download = "Tiny21-C64-Ultimate-v0.6.zip";
            document.body.append(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 30_000);
            status.textContent = "ZIP ready. Unzip it and follow the USB setup below.";
        } catch (error) {
            status.textContent = `${error.message} Check your connection and try again.`;
        } finally {
            button.disabled = false;
        }
    });
}
