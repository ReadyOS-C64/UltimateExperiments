#include "readyfs_plan.h"

#include <string.h>

#ifdef __CC65__
#include "readyfs_reu.h"
#endif


unsigned int readyfs_plan_abi(void) { return RF_PLAN_ABI; }

#ifndef __CC65__
unsigned char readyfs_plan_dispatch(ReadyFsPlanCall *call) {
    if (call == 0 || call->plan == 0) return 0u;
    if (call->operation == RF_PLAN_CALL_INIT) {
        readyfs_plan_init(call->plan, call->capacity, call->write, call->read);
        call->result = 1u;
    } else if (call->operation == RF_PLAN_CALL_ADD) {
        call->result = readyfs_plan_add(call->plan, call->kind, call->flags,
                                        call->stem);
    } else if (call->operation == RF_PLAN_CALL_READ) {
        call->result = readyfs_plan_read(call->plan, call->offset,
                                         call->record, call->output,
                                         call->output_capacity, &call->next);
    } else call->result = 0u;
    return call->result;
}
#endif

static void put_u16(unsigned char *data, unsigned int value) {
    data[0] = (unsigned char)(value & 0xFFu);
    data[1] = (unsigned char)(value >> 8u);
}

static unsigned int get_u16(const unsigned char *data) {
    return (unsigned int)(data[0] | ((unsigned int)data[1] << 8u));
}

static unsigned char call_write(const ReadyFsPlan *plan,
                                unsigned int offset, const void *data,
                                unsigned int length) {
#ifdef __CC65__
    (void)plan;
    if (offset > RF_REU_PLAN_BYTES ||
        length > (unsigned int)(RF_REU_PLAN_BYTES - offset)) return 0u;
    return readyfs_reu_session_store((unsigned int)(RF_REU_PLAN_OFF + offset),
                                     data, length);
#else
    return plan->write != 0 && plan->write(offset, data, length);
#endif
}

static unsigned char call_read(const ReadyFsPlan *plan,
                               unsigned int offset, void *data,
                               unsigned int length) {
#ifdef __CC65__
    (void)plan;
    if (offset > RF_REU_PLAN_BYTES ||
        length > (unsigned int)(RF_REU_PLAN_BYTES - offset)) return 0u;
    return readyfs_reu_session_fetch((unsigned int)(RF_REU_PLAN_OFF + offset),
                                     data, length);
#else
    return plan->read != 0 && plan->read(offset, data, length);
#endif
}

#ifndef __CC65__
void readyfs_plan_init(ReadyFsPlan *plan, unsigned int capacity,
                       ReadyFsPlanWrite write_fn, ReadyFsPlanRead read_fn) {
    memset(plan, 0, sizeof(*plan));
    plan->write = write_fn;
    plan->read = read_fn;
    plan->capacity = capacity;
    plan->last = RF_PLAN_END;
}

unsigned char readyfs_plan_add(ReadyFsPlan *plan, unsigned char kind,
                               unsigned char flags, const char *stem) {
    unsigned char header[RF_PLAN_HEADER_BYTES];
    unsigned int length;
    unsigned int record_bytes;

    if (plan == 0 || stem == 0 ||
#ifndef __CC65__
        plan->write == 0 ||
#endif
        (kind != RF_PLAN_KIND_FILE && kind != RF_PLAN_KIND_DIR)) return 0u;
    length = strlen(stem);
    if (length > 255u || (kind == RF_PLAN_KIND_FILE && length == 0u)) return 0u;
    record_bytes = (unsigned int)(RF_PLAN_HEADER_BYTES + length + 1u);
    if (plan->used > plan->capacity ||
        record_bytes > (unsigned int)(plan->capacity - plan->used)) {
        plan->overflow = 1u;
        return 0u;
    }
    header[0] = kind;
    header[1] = flags;
    put_u16(header + 2u, length);
    put_u16(header + 4u, plan->last);
    if (!call_write(plan, plan->used, header, sizeof(header)) ||
        !call_write(plan, (unsigned int)(plan->used + RF_PLAN_HEADER_BYTES),
                    stem, (unsigned int)(length + 1u))) return 0u;
    plan->last = plan->used;
    plan->used = (unsigned int)(plan->used + record_bytes);
    ++plan->count;
    if (kind == RF_PLAN_KIND_FILE) {
        ++plan->files;
        if ((flags & RF_PLAN_SELECTED) != 0u) ++plan->selected_files;
    } else {
        ++plan->directories;
        if ((flags & RF_PLAN_SELECTED) != 0u) ++plan->selected_directories;
    }
    return 1u;
}

unsigned char readyfs_plan_read(const ReadyFsPlan *plan, unsigned int offset,
                                ReadyFsPlanRecord *record, char *stem,
                                unsigned int stem_capacity,
                                unsigned int *next) {
    unsigned char header[RF_PLAN_HEADER_BYTES];
    unsigned int length;
    unsigned int end;

    if (plan == 0 || record == 0 || stem == 0 ||
#ifndef __CC65__
        plan->read == 0 ||
#endif
        next == 0 || offset == RF_PLAN_END || offset >= plan->used ||
        !call_read(plan, offset, header, sizeof(header))) return 0u;
    length = get_u16(header + 2u);
    end = (unsigned int)(offset + RF_PLAN_HEADER_BYTES + length + 1u);
    if ((header[0] != RF_PLAN_KIND_FILE && header[0] != RF_PLAN_KIND_DIR) ||
        length >= stem_capacity || end <= offset || end > plan->used ||
        !call_read(plan, (unsigned int)(offset + RF_PLAN_HEADER_BYTES), stem,
                   (unsigned int)(length + 1u)) || stem[length] != 0) return 0u;
    record->kind = header[0];
    record->flags = header[1];
    record->stem_len = length;
    record->previous = get_u16(header + 4u);
    *next = end == plan->used ? RF_PLAN_END : end;
    return 1u;
}

unsigned int readyfs_plan_first(const ReadyFsPlan *plan) {
    return plan != 0 && plan->count != 0u ? 0u : RF_PLAN_END;
}
#endif

#ifdef __CC65__
/* C64 sidecar entry: INIT/ADD/READ operate directly on the one-pointer call
 * record. Do not bounce through the public multi-argument API here. */
unsigned char readyfs_plan_dispatch(ReadyFsPlanCall *call) {
    ReadyFsPlan *plan;
    unsigned char header[RF_PLAN_HEADER_BYTES];
    unsigned int length;
    unsigned int record_bytes;
    unsigned int end;

    if (call == 0 || call->plan == 0) return 0u;
    plan = call->plan;
    if (call->operation == RF_PLAN_CALL_INIT) {
        memset(plan, 0, sizeof(*plan));
        plan->capacity = call->capacity;
        plan->last = RF_PLAN_END;
        call->result = 1u;
        return 1u;
    }
    if (call->operation == RF_PLAN_CALL_ADD) {
        if (call->stem == 0 ||
            (call->kind != RF_PLAN_KIND_FILE &&
             call->kind != RF_PLAN_KIND_DIR)) return 0u;
        length = strlen(call->stem);
        if (length > 255u ||
            (call->kind == RF_PLAN_KIND_FILE && length == 0u)) return 0u;
        record_bytes = (unsigned int)(RF_PLAN_HEADER_BYTES + length + 1u);
        if (plan->used > plan->capacity ||
            record_bytes > (unsigned int)(plan->capacity - plan->used)) {
            plan->overflow = 1u;
            return 0u;
        }
        header[0] = call->kind;
        header[1] = call->flags;
        put_u16(header + 2u, length);
        put_u16(header + 4u, plan->last);
        if (!call_write(plan, plan->used, header, sizeof(header)) ||
            !call_write(plan,
                        (unsigned int)(plan->used + RF_PLAN_HEADER_BYTES),
                        call->stem, (unsigned int)(length + 1u))) return 0u;
        plan->last = plan->used;
        plan->used = (unsigned int)(plan->used + record_bytes);
        ++plan->count;
        if (call->kind == RF_PLAN_KIND_FILE) {
            ++plan->files;
            if ((call->flags & RF_PLAN_SELECTED) != 0u) {
                ++plan->selected_files;
            }
        } else {
            ++plan->directories;
            if ((call->flags & RF_PLAN_SELECTED) != 0u) {
                ++plan->selected_directories;
            }
        }
        call->result = 1u;
        return 1u;
    }
    if (call->operation != RF_PLAN_CALL_READ || call->record == 0 ||
        call->output == 0 || call->offset == RF_PLAN_END ||
        call->offset >= plan->used ||
        !call_read(plan, call->offset, header, sizeof(header))) return 0u;
    length = get_u16(header + 2u);
    end = (unsigned int)(call->offset + RF_PLAN_HEADER_BYTES + length + 1u);
    if ((header[0] != RF_PLAN_KIND_FILE &&
         header[0] != RF_PLAN_KIND_DIR) ||
        length >= call->output_capacity || end <= call->offset ||
        end > plan->used ||
        !call_read(plan,
                   (unsigned int)(call->offset + RF_PLAN_HEADER_BYTES),
                   call->output, (unsigned int)(length + 1u)) ||
        call->output[length] != 0) return 0u;
    call->record->kind = header[0];
    call->record->flags = header[1];
    call->record->stem_len = length;
    call->record->previous = get_u16(header + 4u);
    call->next = end == plan->used ? RF_PLAN_END : end;
    call->result = 1u;
    return 1u;
}
#endif
