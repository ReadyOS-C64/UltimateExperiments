test {
    _ = @import("files.zig");
}
test {
    _ = @import("render_text.zig");
}
test {
    _ = @import("overlays.zig");
}
test {
    _ = @import("overlay_startup.zig");
}

test {
    _ = @import("host_input.zig");
}
test {
    _ = @import("cold_phase.zig");
}

test { _ = @import("native_text_display.zig"); }
