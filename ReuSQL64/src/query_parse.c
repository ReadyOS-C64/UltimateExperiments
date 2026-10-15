#include <string.h>

#include "rsql_errors.h"
#include "rsql_query.h"
#include "rsql_query_phase.h"

typedef struct Parser {
    const char* sql;
    rsql_u16 length;
    rsql_u16 offset;
} Parser;

static rsql_u8 folded(char value) {
    if (value >= 'a' && value <= 'z') return (rsql_u8)(value - ('a' - 'A'));
    return (rsql_u8)value;
}

static rsql_u8 is_space(char value) {
    return value == ' ' || value == '\t' || value == '\r' || value == '\n';
}

static rsql_u8 is_name_start(char value) {
    value = (char)folded(value);
    return (value >= 'A' && value <= 'Z') || value == '_';
}

static rsql_u8 is_name_char(char value) {
    value = (char)folded(value);
    return is_name_start(value) || (value >= '0' && value <= '9');
}

static void skip_space(Parser* parser) {
    while (parser->offset < parser->length &&
           is_space(parser->sql[parser->offset])) {
        ++parser->offset;
    }
}

static rsql_u8 keyword(Parser* parser, const char* expected) {
    rsql_u16 start;
    rsql_u16 index = 0u;
    skip_space(parser);
    start = parser->offset;
    while (expected[index] != '\0' && parser->offset < parser->length &&
           folded(parser->sql[parser->offset]) == (rsql_u8)expected[index]) {
        ++parser->offset;
        ++index;
    }
    if (expected[index] != '\0' ||
        (parser->offset < parser->length &&
         is_name_char(parser->sql[parser->offset]))) {
        parser->offset = start;
        return 0u;
    }
    return 1u;
}

static rsql_u8 punctuation(Parser* parser, char expected) {
    skip_space(parser);
    if (parser->offset >= parser->length ||
        parser->sql[parser->offset] != expected) return 0u;
    ++parser->offset;
    return 1u;
}

static rsql_u8 ordinal_mask(rsql_u8 ordinal) {
    rsql_u8 mask = 1u;
    if (ordinal >= 8u) return 0u;
    while (ordinal != 0u) {
        mask <<= 1u;
        --ordinal;
    }
    return mask;
}

static rsql_u8 name(Parser* parser, char* destination, rsql_u8 maximum) {
    rsql_u8 length = 0u;
    skip_space(parser);
    if (parser->offset >= parser->length ||
        !is_name_start(parser->sql[parser->offset])) return 0u;
    while (parser->offset < parser->length &&
           is_name_char(parser->sql[parser->offset])) {
        if (length >= maximum) return 0u;
        destination[length++] = (char)folded(parser->sql[parser->offset++]);
    }
    destination[length] = '\0';
    return 1u;
}

/* Qualified query references are kept in the existing 16-byte column-name
 * slots. Long table names can always use a short AS alias. */
static rsql_u8 qualified_name(Parser* parser, char* destination) {
    rsql_u8 length;
    if (!name(parser, destination, RSQL_COLUMN_NAME_MAX)) return 0u;
    length = (rsql_u8)strlen(destination);
    if (!punctuation(parser, '.')) return 1u;
    if (length >= RSQL_COLUMN_NAME_MAX) return 0u;
    destination[length++] = '.';
    if (!name(parser, &destination[length],
              (rsql_u8)(RSQL_COLUMN_NAME_MAX - length))) return 0u;
    return 1u;
}

static rsql_u8 number(Parser* parser, rsql_u16* value_out) {
    unsigned long value = 0ul;
    rsql_u8 digits = 0u;
    skip_space(parser);
    while (parser->offset < parser->length &&
           parser->sql[parser->offset] >= '0' &&
           parser->sql[parser->offset] <= '9') {
        value = value * 10ul +
            (unsigned long)(parser->sql[parser->offset++] - '0');
        if (value > 65535ul) return 0u;
        digits = 1u;
    }
    if (!digits) return 0u;
    *value_out = (rsql_u16)value;
    return 1u;
}

static rsql_u8 integer_literal(Parser* parser, RsqlI64* value_out) {
    rsql_u16 carry;
    rsql_u8 negative = 0u;
    rsql_u8 digits = 0u;
    rsql_u8 byte;
    rsql_u8 index;
    skip_space(parser);
    memset(value_out->bytes, 0, sizeof(value_out->bytes));
    if (parser->offset < parser->length &&
        (parser->sql[parser->offset] == '-' ||
         parser->sql[parser->offset] == '+')) {
        negative = parser->sql[parser->offset] == '-';
        ++parser->offset;
    }
    while (parser->offset < parser->length &&
           parser->sql[parser->offset] >= '0' &&
           parser->sql[parser->offset] <= '9') {
        carry = (rsql_u16)(parser->sql[parser->offset++] - '0');
        for (index = 0u; index < sizeof(value_out->bytes); ++index) {
            carry = (rsql_u16)((rsql_u16)value_out->bytes[index] * 10u + carry);
            value_out->bytes[index] = (rsql_u8)carry;
            carry >>= 8u;
        }
        if (carry != 0u) return 0u;
        digits = 1u;
    }
    if (!digits) return 0u;
    if (negative) {
        carry = 1u;
        for (index = 0u; index < sizeof(value_out->bytes); ++index) {
            byte = (rsql_u8)~value_out->bytes[index];
            carry = (rsql_u16)byte + carry;
            value_out->bytes[index] = (rsql_u8)carry;
            carry >>= 8u;
        }
    }
    return 1u;
}

static rsql_u8 numeric_literal(Parser* parser, RsqlParsedValue* value) {
    rsql_u16 start;
    rsql_u16 length;
    rsql_u16 integer_end;
    rsql_u8 digits = 0u;
    rsql_u8 exponent_digits = 0u;
    rsql_u8 is_float = 0u;
    Parser integer_parser;
    skip_space(parser);
    start = parser->offset;
    if (parser->offset < parser->length &&
        (parser->sql[parser->offset] == '-' ||
         parser->sql[parser->offset] == '+')) ++parser->offset;
    while (parser->offset < parser->length &&
           parser->sql[parser->offset] >= '0' &&
           parser->sql[parser->offset] <= '9') {
        ++parser->offset;
        digits = 1u;
    }
    integer_end = parser->offset;
    if (parser->offset < parser->length &&
        parser->sql[parser->offset] == '.') {
        is_float = 1u;
        ++parser->offset;
        while (parser->offset < parser->length &&
               parser->sql[parser->offset] >= '0' &&
               parser->sql[parser->offset] <= '9') {
            ++parser->offset;
            digits = 1u;
        }
    }
    if (!digits) {
        parser->offset = start;
        return 0u;
    }
    if (parser->offset < parser->length &&
        folded(parser->sql[parser->offset]) == 'E') {
        is_float = 1u;
        ++parser->offset;
        if (parser->offset < parser->length &&
            (parser->sql[parser->offset] == '-' ||
             parser->sql[parser->offset] == '+')) ++parser->offset;
        while (parser->offset < parser->length &&
               parser->sql[parser->offset] >= '0' &&
               parser->sql[parser->offset] <= '9') {
            ++parser->offset;
            exponent_digits = 1u;
        }
        if (!exponent_digits) {
            parser->offset = start;
            return 0u;
        }
    }
    length = (rsql_u16)(parser->offset - start);
    if (length == 0u || length > RSQL_VALUE_STRING_MAX) {
        parser->offset = start;
        return 0u;
    }
    memcpy(value->string, &parser->sql[start], length);
    value->string[length] = '\0';
    value->length = (rsql_u8)length;
    if (is_float) {
        value->kind = RSQL_VALUE_FLOAT;
        return 1u;
    }
    integer_parser = *parser;
    integer_parser.offset = start;
    integer_parser.length = integer_end;
    if (!integer_literal(&integer_parser, &value->integer) ||
        integer_parser.offset != integer_end) {
        parser->offset = start;
        return 0u;
    }
    value->kind = RSQL_VALUE_INTEGER;
    return 1u;
}

static rsql_u8 string_literal(Parser* parser, RsqlParsedValue* value) {
    rsql_u8 length = 0u;
    char byte;
    skip_space(parser);
    if (parser->offset >= parser->length || parser->sql[parser->offset] != '\'') {
        return 0u;
    }
    ++parser->offset;
    while (parser->offset < parser->length) {
        byte = parser->sql[parser->offset++];
        if (byte == '\'') {
            if (parser->offset < parser->length &&
                parser->sql[parser->offset] == '\'') {
                ++parser->offset;
            } else {
                value->kind = RSQL_VALUE_STRING;
                value->length = length;
                value->string[length] = '\0';
                return 1u;
            }
        }
        if (length >= RSQL_VALUE_STRING_MAX) return 0u;
        value->string[length++] = byte;
    }
    return 0u;
}

static rsql_u8 hex_digit(char byte, rsql_u8* value_out) {
    byte = (char)folded(byte);
    if (byte >= '0' && byte <= '9') {
        *value_out = (rsql_u8)(byte - '0');
        return 1u;
    }
    if (byte >= 'A' && byte <= 'F') {
        *value_out = (rsql_u8)(byte - 'A' + 10u);
        return 1u;
    }
    return 0u;
}

/* SQL binary literal. Decode in the parser so zero bytes survive phase
 * changes and the metadata phase receives a bounded byte vector. */
static rsql_u8 binary_literal(Parser* parser, RsqlParsedValue* value) {
    rsql_u16 start;
    rsql_u8 high;
    rsql_u8 low;
    rsql_u8 length = 0u;
    skip_space(parser);
    start = parser->offset;
    if ((rsql_u16)(parser->offset + 1u) >= parser->length ||
        folded(parser->sql[parser->offset]) != 'X' ||
        parser->sql[parser->offset + 1u] != '\'') return 0u;
    parser->offset = (rsql_u16)(parser->offset + 2u);
    while (parser->offset < parser->length &&
           parser->sql[parser->offset] != '\'') {
        if (length >= RSQL_VALUE_STRING_MAX ||
            !hex_digit(parser->sql[parser->offset++], &high) ||
            parser->offset >= parser->length ||
            !hex_digit(parser->sql[parser->offset++], &low)) {
            parser->offset = start;
            return 0u;
        }
        value->string[length++] = (char)((high << 4u) | low);
    }
    if (parser->offset >= parser->length ||
        parser->sql[parser->offset++] != '\'') {
        parser->offset = start;
        return 0u;
    }
    value->kind = RSQL_VALUE_BINARY;
    value->length = length;
    return 1u;
}

static rsql_u8 enum_literal(Parser* parser, RsqlParsedValue* value) {
    rsql_u16 start = parser->offset;
    rsql_u8 length;
    if (!name(parser, value->string, RSQL_ENUM_NAME_MAX)) return 0u;
    length = (rsql_u8)strlen(value->string);
    if (!punctuation(parser, '.')) {
        parser->offset = start;
        return 0u;
    }
    value->string[length++] = '.';
    if (!name(parser, &value->string[length], RSQL_ENUM_MEMBER_NAME_MAX)) {
        parser->offset = start;
        return 0u;
    }
    value->kind = RSQL_VALUE_ENUM;
    value->length = (rsql_u8)strlen(value->string);
    return 1u;
}

static rsql_u8 parse_value(Parser* parser, RsqlParsedValue* value) {
    memset(value, 0, sizeof(*value));
    if (keyword(parser, "NULL")) {
        value->kind = RSQL_VALUE_NULL;
        return 1u;
    }
    if (keyword(parser, "TRUE")) {
        value->kind = RSQL_VALUE_BOOLEAN;
        value->integer.bytes[0] = 1u;
        return 1u;
    }
    if (keyword(parser, "FALSE")) {
        value->kind = RSQL_VALUE_BOOLEAN;
        return 1u;
    }
    if (binary_literal(parser, value)) return 1u;
    if (string_literal(parser, value)) return 1u;
    if (enum_literal(parser, value)) return 1u;
    if (numeric_literal(parser, value)) return 1u;
    return 0u;
}

static rsql_u8 parse_predicate_operator(Parser* parser, rsql_u8* op_out) {
    skip_space(parser);
    if (parser->offset >= parser->length) return 0u;
    if (parser->sql[parser->offset] == '=') {
        ++parser->offset;
        *op_out = RSQL_PRED_EQ;
        return 1u;
    }
    if (parser->sql[parser->offset] == '!') {
        ++parser->offset;
        if (parser->offset >= parser->length ||
            parser->sql[parser->offset++] != '=') return 0u;
        *op_out = RSQL_PRED_NE;
        return 1u;
    }
    if (parser->sql[parser->offset] == '<') {
        ++parser->offset;
        if (parser->offset < parser->length &&
            parser->sql[parser->offset] == '=') {
            ++parser->offset;
            *op_out = RSQL_PRED_LE;
        } else if (parser->offset < parser->length &&
                   parser->sql[parser->offset] == '>') {
            ++parser->offset;
            *op_out = RSQL_PRED_NE;
        } else *op_out = RSQL_PRED_LT;
        return 1u;
    }
    if (parser->sql[parser->offset] == '>') {
        ++parser->offset;
        if (parser->offset < parser->length &&
            parser->sql[parser->offset] == '=') {
            ++parser->offset;
            *op_out = RSQL_PRED_GE;
        } else *op_out = RSQL_PRED_GT;
        return 1u;
    }
    return 0u;
}

static rsql_u8 emit_bool(rsql_u8 opcode) {
    if (g_rsql_statement.bool_program_count >= RSQL_BOOL_PROGRAM_MAX) {
        return 0u;
    }
    g_rsql_statement.bool_program[g_rsql_statement.bool_program_count++] =
        opcode;
    return 1u;
}

static rsql_u8 parse_bool_or(Parser* parser);

static rsql_u8 emit_subquery_bool(rsql_u8 opcode) {
    if (g_rsql_statement.nested_exists == 2u) {
        if (g_rsql_statement.nested_bool_program_count >=
            RSQL_BOOL_PROGRAM_MAX) return 0u;
        RSQL_NESTED_BOOL_PROGRAM[
            g_rsql_statement.nested_bool_program_count++] = opcode;
        return 1u;
    }
    if (g_rsql_statement.subquery_bool_program_count >=
        RSQL_BOOL_PROGRAM_MAX) return 0u;
    g_rsql_statement.subquery_bool_program[
        g_rsql_statement.subquery_bool_program_count++] = opcode;
    return 1u;
}

static rsql_u8 parse_subquery_bool_or(Parser* parser);
static rsql_u8 parse_subquery_predicate_term(Parser* parser);
static rsql_u8 parse_subquery(Parser* parser, rsql_u8 kind);

/* SELECT statements do not otherwise use the DDL column/value vectors.  The
 * bounded subquery parser reuses them for its private predicate program:
 * columns[i].name is the left operand, columns[i].type.tag is the operator,
 * and values[i] is the right operand. */
static rsql_u8 parse_subquery_predicate_term(Parser* parser) {
    RsqlParsedColumn* predicate;
    RsqlParsedValue* value;
    rsql_u8 index;
    rsql_u8 negate = 0u;
    if (g_rsql_statement.subquery_predicate_count >=
        RSQL_PREDICATES_MAX) return 0u;
    index = g_rsql_statement.subquery_predicate_count;
    predicate = &g_rsql_statement.columns[index];
    value = &g_rsql_statement.values[index];
    memset(predicate, 0, sizeof(*predicate));
    memset(value, 0, sizeof(*value));
    if (g_rsql_statement.nested_exists != 2u && keyword(parser, "EXISTS")) {
        predicate->type.tag = RSQL_PRED_SUBQUERY;
        predicate->type.flags = RSQL_SUBQUERY_EXISTS;
        ++g_rsql_statement.subquery_predicate_count;
        if (!parse_subquery(parser, RSQL_SUBQUERY_EXISTS)) {
            return 0u;
        }
        return emit_subquery_bool(index);
    }
    if (!qualified_name(parser, predicate->name)) return 0u;
    if (keyword(parser, "IS")) {
        if (keyword(parser, "NOT")) {
            if (!keyword(parser, "NULL")) return 0u;
            predicate->type.tag = RSQL_PRED_IS_NOT_NULL;
        } else {
            if (!keyword(parser, "NULL")) return 0u;
            predicate->type.tag = RSQL_PRED_IS_NULL;
        }
        value->kind = RSQL_VALUE_NULL;
    } else if (keyword(parser, "IN")) {
        predicate->type.tag = RSQL_PRED_SUBQUERY;
        predicate->type.flags = RSQL_SUBQUERY_IN;
        ++g_rsql_statement.subquery_predicate_count;
        if (!parse_subquery(parser, RSQL_SUBQUERY_IN)) {
            return 0u;
        }
        return emit_subquery_bool(index);
    } else if (keyword(parser, "LIKE")) {
        predicate->type.tag = RSQL_PRED_LIKE;
        if (!parse_value(parser, value)) return 0u;
    } else if (keyword(parser, "NOT")) {
        if (keyword(parser, "IN")) {
            predicate->type.tag = RSQL_PRED_SUBQUERY;
            predicate->type.flags = RSQL_SUBQUERY_IN;
            ++g_rsql_statement.subquery_predicate_count;
            if (!parse_subquery(parser, RSQL_SUBQUERY_IN)) {
                return 0u;
            }
            if (!emit_subquery_bool(index)) return 0u;
            return emit_subquery_bool(RSQL_BOOL_NOT);
        }
        if (!keyword(parser, "LIKE")) return 0u;
        predicate->type.tag = RSQL_PRED_LIKE;
        if (!parse_value(parser, value)) return 0u;
        negate = 1u;
    } else {
        rsql_u16 value_start;
        if (!parse_predicate_operator(parser, &predicate->type.tag)) return 0u;
        predicate->type.auxiliary = predicate->type.tag;
        predicate->type.tag = RSQL_PRED_SUBQUERY;
        predicate->type.flags = RSQL_SUBQUERY_SCALAR;
        ++g_rsql_statement.subquery_predicate_count;
        value_start = parser->offset;
        if (parse_subquery(parser, RSQL_SUBQUERY_SCALAR)) {
            return emit_subquery_bool(index);
        }
        --g_rsql_statement.subquery_predicate_count;
        parser->offset = value_start;
        predicate->type.tag = (rsql_u8)predicate->type.auxiliary;
        predicate->type.flags = 0u;
        predicate->type.auxiliary = 0u;
        if (!parse_value(parser, value)) return 0u;
    }
    ++g_rsql_statement.subquery_predicate_count;
    if (!emit_subquery_bool(index)) return 0u;
    if (negate && !emit_subquery_bool(RSQL_BOOL_NOT)) return 0u;
    return 1u;
}

static rsql_u8 parse_subquery_bool_primary(Parser* parser) {
    if (punctuation(parser, '(')) {
        if (!parse_subquery_bool_or(parser) || !punctuation(parser, ')')) {
            return 0u;
        }
        return 1u;
    }
    return parse_subquery_predicate_term(parser);
}

static rsql_u8 parse_subquery_bool_not(Parser* parser) {
    if (keyword(parser, "NOT")) {
        if (!parse_subquery_bool_not(parser)) return 0u;
        return emit_subquery_bool(RSQL_BOOL_NOT);
    }
    return parse_subquery_bool_primary(parser);
}

static rsql_u8 parse_subquery_bool_and(Parser* parser) {
    if (!parse_subquery_bool_not(parser)) return 0u;
    while (keyword(parser, "AND")) {
        if (!parse_subquery_bool_not(parser) ||
            !emit_subquery_bool(RSQL_BOOL_AND)) return 0u;
    }
    return 1u;
}

static rsql_u8 parse_subquery_bool_or(Parser* parser) {
    if (!parse_subquery_bool_and(parser)) return 0u;
    while (keyword(parser, "OR")) {
        if (!parse_subquery_bool_and(parser) ||
            !emit_subquery_bool(RSQL_BOOL_OR)) return 0u;
    }
    return 1u;
}

static rsql_u8 parse_subquery(Parser* parser, rsql_u8 kind) {
    RsqlParsedColumn* nested_predicate;
    char* projection;
    rsql_u16 projection_start;
    rsql_u8 nested = g_rsql_statement.subquery_kind != RSQL_SUBQUERY_NONE;
    if ((nested && (g_rsql_statement.nested_exists ||
                    g_rsql_statement.join_type != RSQL_JOIN_NONE)) ||
        !punctuation(parser, '(') || !keyword(parser, "SELECT")) return 0u;
    if (nested) {
        nested_predicate = &g_rsql_statement.columns[
            g_rsql_statement.subquery_predicate_count - 1u];
        projection = nested_predicate->type_name;
    } else {
        g_rsql_statement.subquery_kind = kind;
        projection = g_rsql_statement.subquery_projection;
    }
    projection_start = parser->offset;
    if (kind == RSQL_SUBQUERY_EXISTS && punctuation(parser, '*')) {
        projection[0] = '\0';
    } else {
        skip_space(parser);
        if (kind == RSQL_SUBQUERY_EXISTS &&
            parser->offset < parser->length &&
            parser->sql[parser->offset] == '1' &&
            ((rsql_u16)(parser->offset + 1u) == parser->length ||
             !is_name_char(parser->sql[parser->offset + 1u]))) {
            ++parser->offset;
            projection[0] = '\0';
        } else if (!qualified_name(parser, projection)) {
            parser->offset = projection_start;
            return 0u;
        }
    }
    if (!keyword(parser, "FROM") ||
        !name(parser, g_rsql_statement.subquery_table_name,
              RSQL_TABLE_NAME_MAX)) return 0u;
    if (nested) g_rsql_statement.subquery_table_alias[0] = '\0';
    if (keyword(parser, "AS") &&
        !name(parser, g_rsql_statement.subquery_table_alias,
              RSQL_COLUMN_NAME_MAX)) return 0u;
    if (!nested && g_rsql_statement.join_type == RSQL_JOIN_NONE) {
        strcpy(g_rsql_statement.join_table_name,
               g_rsql_statement.subquery_table_name);
        strcpy(g_rsql_statement.join_table_alias,
               g_rsql_statement.subquery_table_alias);
    }
    if (nested) {
        g_rsql_statement.nested_exists = 2u;
        g_rsql_statement.nested_predicate_start =
            g_rsql_statement.subquery_predicate_count;
    }
    if (keyword(parser, "WHERE") && !parse_subquery_bool_or(parser)) return 0u;
    if (nested) {
        g_rsql_statement.nested_predicate_count = (rsql_u8)
            (g_rsql_statement.subquery_predicate_count -
             g_rsql_statement.nested_predicate_start);
        g_rsql_statement.nested_exists = 1u;
    }
    return punctuation(parser, ')');
}

static rsql_u8 parse_predicate_term(Parser* parser) {
    RsqlParsedPredicate* predicate;
    rsql_u8 index;
    rsql_u8 negate = 0u;
    if (g_rsql_statement.predicate_count >= RSQL_PREDICATES_MAX) return 0u;
    index = g_rsql_statement.predicate_count;
    predicate = &g_rsql_statement.predicates[index];
    memset(predicate, 0, sizeof(*predicate));
    if (keyword(parser, "EXISTS")) {
        predicate->op = RSQL_PRED_SUBQUERY;
        if (!parse_subquery(parser, RSQL_SUBQUERY_EXISTS)) return 0u;
        ++g_rsql_statement.predicate_count;
        return emit_bool(index);
    }
    if (!qualified_name(parser, predicate->column)) return 0u;
    if (keyword(parser, "IS")) {
        if (keyword(parser, "NOT")) {
            if (!keyword(parser, "NULL")) return 0u;
            predicate->op = RSQL_PRED_IS_NOT_NULL;
        } else {
            if (!keyword(parser, "NULL")) return 0u;
            predicate->op = RSQL_PRED_IS_NULL;
        }
        predicate->value.kind = RSQL_VALUE_NULL;
    } else if (keyword(parser, "IN")) {
        predicate->op = RSQL_PRED_SUBQUERY;
        if (!parse_subquery(parser, RSQL_SUBQUERY_IN)) return 0u;
    } else if (keyword(parser, "LIKE")) {
        predicate->op = RSQL_PRED_LIKE;
        if (!parse_value(parser, &predicate->value)) return 0u;
    } else if (keyword(parser, "NOT")) {
        if (keyword(parser, "IN")) {
            predicate->op = RSQL_PRED_SUBQUERY;
            if (!parse_subquery(parser, RSQL_SUBQUERY_IN)) return 0u;
            negate = 1u;
        } else {
            if (!keyword(parser, "LIKE")) return 0u;
            predicate->op = RSQL_PRED_LIKE;
            if (!parse_value(parser, &predicate->value)) return 0u;
            negate = 1u;
        }
    } else {
        rsql_u16 value_start;
        if (!parse_predicate_operator(parser, &predicate->op)) return 0u;
        value_start = parser->offset;
        if (parse_subquery(parser, RSQL_SUBQUERY_SCALAR)) {
            g_rsql_statement.subquery_compare_op = predicate->op;
            predicate->op = RSQL_PRED_SUBQUERY;
        } else {
            parser->offset = value_start;
            if (!parse_value(parser, &predicate->value)) return 0u;
        }
    }
    ++g_rsql_statement.predicate_count;
    if (!emit_bool(index)) return 0u;
    if (negate && !emit_bool(RSQL_BOOL_NOT)) return 0u;
    return 1u;
}

static rsql_u8 parse_bool_primary(Parser* parser) {
    if (punctuation(parser, '(')) {
        if (!parse_bool_or(parser) || !punctuation(parser, ')')) return 0u;
        return 1u;
    }
    return parse_predicate_term(parser);
}

static rsql_u8 parse_bool_not(Parser* parser) {
    if (keyword(parser, "NOT")) {
        if (!parse_bool_not(parser)) return 0u;
        return emit_bool(RSQL_BOOL_NOT);
    }
    return parse_bool_primary(parser);
}

static rsql_u8 parse_bool_and(Parser* parser) {
    if (!parse_bool_not(parser)) return 0u;
    while (keyword(parser, "AND")) {
        if (!parse_bool_not(parser) || !emit_bool(RSQL_BOOL_AND)) return 0u;
    }
    return 1u;
}

static rsql_u8 parse_bool_or(Parser* parser) {
    if (!parse_bool_and(parser)) return 0u;
    while (keyword(parser, "OR")) {
        if (!parse_bool_and(parser) || !emit_bool(RSQL_BOOL_OR)) return 0u;
    }
    return 1u;
}

/* SELECT reuses enum_members as a descending packed scalar-literal pool.
 * ORDER descriptors grow upward in the same 256-byte area; the completed
 * parse rejects overlap. group_columns is otherwise unused by scan-mode
 * literal scalar projections and retains each pool offset and length. */
static rsql_u16 g_scalar_literal_pool_start;

static rsql_u8 parse_index_hint(Parser* parser, char* destination,
                                rsql_u8 source_mask) {
    if (!keyword(parser, "USING")) return 1u;
    if (!keyword(parser, "INDEX") ||
        !name(parser, destination, RSQL_TABLE_NAME_MAX)) return 0u;
    g_rsql_statement.using_index |= source_mask;
    return 1u;
}

static rsql_u8 store_scalar_literal(rsql_u8 index,
                                    const RsqlParsedValue* literal) {
    rsql_u16 length = literal->length;
    if (length > g_scalar_literal_pool_start) return 0u;
    if (length != 0u) {
        g_scalar_literal_pool_start =
            (rsql_u16)(g_scalar_literal_pool_start - length);
        memcpy((rsql_u8*)&g_rsql_statement.enum_members[0][0] +
                   g_scalar_literal_pool_start,
               literal->string, length);
    }
    g_rsql_statement.group_columns[index][0] =
        (char)(length ? g_scalar_literal_pool_start : 0u);
    g_rsql_statement.group_columns[index][1] = (char)length;
    return 1u;
}

static rsql_u8 store_aggregate_group_name(rsql_u8 index,
                                          const char* group_name) {
    rsql_u16 length = (rsql_u16)strlen(group_name) + 1u;
    if (length > g_scalar_literal_pool_start) return 0u;
    g_scalar_literal_pool_start =
        (rsql_u16)(g_scalar_literal_pool_start - length);
    memcpy((rsql_u8*)&g_rsql_statement.enum_members[0][0] +
               g_scalar_literal_pool_start,
           group_name, length);
    g_rsql_statement.aggregate_group_offsets[index] =
        (rsql_u8)g_scalar_literal_pool_start;
    return 1u;
}

static rsql_u8 parse_string_operand(Parser* parser, char* name_out,
                                    RsqlParsedValue* literal_out,
                                    rsql_u8* literal) {
    skip_space(parser);
    if (parser->offset < parser->length &&
        parser->sql[parser->offset] == '\'') {
        memset(literal_out, 0, sizeof(*literal_out));
        if (!parse_value(parser, literal_out) ||
            literal_out->kind != RSQL_VALUE_STRING) return 0u;
        *literal = 1u;
        return 1u;
    }
    *literal = 0u;
    return qualified_name(parser, name_out);
}

static rsql_u8 parse_concat_operands(Parser* parser, rsql_u8 index,
                                     rsql_u8 parenthesized) {
    RsqlParsedValue right_literal;
    rsql_u8 left_is_literal;
    rsql_u8 right_is_literal;
    rsql_u16 combined;
    if (!parse_string_operand(parser, g_rsql_statement.projections[index],
            &g_rsql_statement.values[index], &left_is_literal)) return 0u;
    if (parenthesized) {
        if (!punctuation(parser, ',')) return 0u;
    } else if (!punctuation(parser, '|') || !punctuation(parser, '|')) {
        return 0u;
    }
    if (left_is_literal) {
        if (!parse_string_operand(parser, g_rsql_statement.projections[index],
                &right_literal, &right_is_literal)) return 0u;
    } else {
        if (!parse_string_operand(parser, g_rsql_statement.group_columns[index],
                &g_rsql_statement.values[index], &right_is_literal)) return 0u;
    }
    if (parenthesized && !punctuation(parser, ')')) return 0u;
    if (left_is_literal && right_is_literal) {
        combined = (rsql_u16)g_rsql_statement.values[index].length +
            right_literal.length;
        if (combined > RSQL_VALUE_STRING_MAX) return 0u;
        memcpy(&g_rsql_statement.values[index].string[
                   g_rsql_statement.values[index].length],
               right_literal.string, right_literal.length);
        g_rsql_statement.values[index].length = (rsql_u8)combined;
        g_rsql_statement.values[index].string[combined] = '\0';
        g_rsql_statement.projection_aggregate[index] = RSQL_SCALAR_STRING;
    } else {
        g_rsql_statement.projection_aggregate[index] = RSQL_SCALAR_CONCAT;
        if (left_is_literal) {
            g_rsql_statement.projection_aggregate[index] |=
                RSQL_PROJECTION_LITERAL_LEFT;
        } else if (right_is_literal) {
            g_rsql_statement.projection_aggregate[index] |=
                RSQL_PROJECTION_LITERAL_RIGHT;
        }
    }
    return !left_is_literal && !right_is_literal ? 1u :
        store_scalar_literal(index, &g_rsql_statement.values[index]);
}

static rsql_u8 parse_select_item(Parser* parser, rsql_u8 index) {
    rsql_u8 aggregate = RSQL_AGG_NONE;
    rsql_u8 literal;
    rsql_u16 start;
    rsql_u16 count = 0xFFFFu;
    rsql_u16 item_start;
    if (keyword(parser, "COUNT")) aggregate = RSQL_AGG_COUNT;
    else if (keyword(parser, "SUM")) aggregate = RSQL_AGG_SUM;
    else if (keyword(parser, "AVG")) aggregate = RSQL_AGG_AVG;
    else if (keyword(parser, "MIN")) aggregate = RSQL_AGG_MIN;
    else if (keyword(parser, "MAX")) aggregate = RSQL_AGG_MAX;
    if (aggregate != RSQL_AGG_NONE) {
        if (!punctuation(parser, '(')) return 0u;
        if (aggregate == RSQL_AGG_COUNT && punctuation(parser, '*')) {
            aggregate = RSQL_AGG_COUNT_STAR;
            g_rsql_statement.projections[index][0] = '\0';
        } else if (!qualified_name(parser,
                         g_rsql_statement.projections[index])) return 0u;
        if (!punctuation(parser, ')')) return 0u;
        g_rsql_statement.projection_aggregate[index] = aggregate;
        return 1u;
    }
    if (keyword(parser, "LENGTH")) {
        if (!punctuation(parser, '(') ||
            !parse_string_operand(parser,
                g_rsql_statement.projections[index],
                &g_rsql_statement.values[index], &literal) ||
            !punctuation(parser, ')')) return 0u;
        g_rsql_statement.projection_aggregate[index] = RSQL_SCALAR_LENGTH;
        if (literal) g_rsql_statement.projection_aggregate[index] |=
            RSQL_PROJECTION_LITERAL_LEFT;
        return !literal || store_scalar_literal(
            index, &g_rsql_statement.values[index]);
    }
    if (keyword(parser, "SUBSTR") || keyword(parser, "SUBSTRING")) {
        if (!punctuation(parser, '(') ||
            !parse_string_operand(parser,
                g_rsql_statement.projections[index],
                &g_rsql_statement.values[index], &literal) ||
            !punctuation(parser, ',') || !number(parser, &start) ||
            start == 0u) return 0u;
        if (punctuation(parser, ',') && !number(parser, &count)) return 0u;
        if (!punctuation(parser, ')')) return 0u;
        g_rsql_statement.enum_values[index] = start;
        g_rsql_statement.enum_values[RSQL_TABLE_COLUMNS_MAX + index] = count;
        g_rsql_statement.projection_aggregate[index] = RSQL_SCALAR_SUBSTR;
        if (literal) g_rsql_statement.projection_aggregate[index] |=
            RSQL_PROJECTION_LITERAL_LEFT;
        return !literal || store_scalar_literal(
            index, &g_rsql_statement.values[index]);
    }
    if (keyword(parser, "CONCAT")) {
        if (!punctuation(parser, '(')) return 0u;
        return parse_concat_operands(parser, index, 1u);
    }
    item_start = parser->offset;
    if (!parse_string_operand(parser, g_rsql_statement.projections[index],
            &g_rsql_statement.values[index], &literal)) return 0u;
    if (punctuation(parser, '|')) {
        parser->offset = item_start;
        return parse_concat_operands(parser, index, 0u);
    }
    if (!literal) return 1u;
    g_rsql_statement.projection_aggregate[index] = RSQL_SCALAR_STRING;
    return store_scalar_literal(index, &g_rsql_statement.values[index]);
}

static rsql_u8 parse_type(Parser* parser, RsqlTypeSpec* type,
                          char* type_name) {
    memset(type, 0, sizeof(*type));
    type_name[0] = '\0';
    if (keyword(parser, "BOOLEAN")) type->tag = RSQL_TYPE_BOOLEAN;
    else if (keyword(parser, "I8")) type->tag = RSQL_TYPE_I8;
    else if (keyword(parser, "I16")) type->tag = RSQL_TYPE_I16;
    else if (keyword(parser, "I32")) type->tag = RSQL_TYPE_I32;
    else if (keyword(parser, "I64")) type->tag = RSQL_TYPE_I64;
    else if (keyword(parser, "FIXED8_8")) type->tag = RSQL_TYPE_FIXED8_8;
    else if (keyword(parser, "FLOAT")) type->tag = RSQL_TYPE_FLOAT5;
    else if (keyword(parser, "TEXT")) type->tag = RSQL_TYPE_TEXT;
    else if (keyword(parser, "BLOB")) type->tag = RSQL_TYPE_BLOB;
    else if (keyword(parser, "CHAR")) {
        type->tag = RSQL_TYPE_CHAR;
        if (!punctuation(parser, '(') ||
            !number(parser, &type->parameter) ||
            type->parameter == 0u ||
            !punctuation(parser, ')')) return 0u;
    } else if (name(parser, type_name, RSQL_ENUM_NAME_MAX)) {
        /* Metadata resolves a named enum and supplies tag plus catalog ID. */
        type->tag = 0u;
    } else return 0u;
    return 1u;
}

static rsql_u8 syntax(Parser* parser) {
    g_rsql_statement.error_offset = parser->offset;
    return RSQL_ERR_SYNTAX;
}

rsql_u8 __fastcall__ rsql_query_parse(const char* sql, rsql_u16 length) {
    Parser parser;
    RsqlParsedColumn* column;
    rsql_u16 enum_value;
    rsql_u16 select_offset;
    rsql_u8 nullable;
    rsql_u8 index;
    rsql_u8 temporary;
    rsql_u8 rc;

    memset(&g_rsql_statement, 0, sizeof(g_rsql_statement));
    g_scalar_literal_pool_start = sizeof(g_rsql_statement.enum_members);
    if (!sql || length == 0u) return RSQL_ERR_INVALID_ARGUMENT;
    parser.sql = sql;
    parser.length = length;
    parser.offset = 0u;

    if (keyword(&parser, "CREATE")) {
        temporary = keyword(&parser, "TEMP") ||
            keyword(&parser, "TEMPORARY");
        if (keyword(&parser, "TABLE")) {
        g_rsql_statement.kind = RSQL_STMT_CREATE_TABLE;
        if (!name(&parser, g_rsql_statement.table_name,
                  RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        g_rsql_statement.enum_width = temporary;
        if (keyword(&parser, "AS")) {
            strcpy((char*)g_rsql_execution.row,
                   g_rsql_statement.table_name);
            select_offset = parser.offset;
            rc = rsql_query_parse(parser.sql + select_offset,
                                  (rsql_u16)(parser.length - select_offset));
            if (rc != RSQL_OK) {
                g_rsql_statement.error_offset = (rsql_u16)
                    (g_rsql_statement.error_offset + select_offset);
                return rc;
            }
            if (g_rsql_statement.kind != RSQL_STMT_SELECT) {
                g_rsql_statement.error_offset = select_offset;
                return RSQL_ERR_SYNTAX;
            }
            if (g_rsql_statement.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN) {
                strcpy(RSQL_WIDE_CTAS_NAME(g_rsql_statement),
                       (const char*)g_rsql_execution.row);
            } else {
                strcpy(g_rsql_statement.columns[0].name,
                       (const char*)g_rsql_execution.row);
            }
            g_rsql_statement.enum_width = temporary;
            g_rsql_statement.kind = RSQL_STMT_CREATE_TABLE_AS;
            return RSQL_OK;
        }
        if (!punctuation(&parser, '(')) return syntax(&parser);

        for (;;) {
            if (g_rsql_statement.column_count >= RSQL_TABLE_COLUMNS_MAX) {
                return syntax(&parser);
            }
            column = &g_rsql_statement.columns[g_rsql_statement.column_count];
            if (!name(&parser, column->name, RSQL_COLUMN_NAME_MAX)) {
                return syntax(&parser);
            }
            if (!parse_type(&parser, &column->type, column->type_name)) {
                return syntax(&parser);
            }
            nullable = 0u;
            if (keyword(&parser, "NOT")) {
                if (!keyword(&parser, "NULL")) return syntax(&parser);
            } else if (keyword(&parser, "NULL")) {
                nullable = 1u;
            }
            if (nullable) column->type.flags |= RSQL_TYPE_FLAG_NULLABLE;
            ++g_rsql_statement.column_count;
            if (punctuation(&parser, ')')) break;
            if (!punctuation(&parser, ',')) return syntax(&parser);
        }
        } else if (!temporary && keyword(&parser, "TYPE")) {
            g_rsql_statement.kind = RSQL_STMT_CREATE_ENUM;
            if (!name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX) || !keyword(&parser, "AS")) {
                return syntax(&parser);
            }
            if (keyword(&parser, "ENUM8")) {
                g_rsql_statement.enum_width = 1u;
            } else if (keyword(&parser, "ENUM16")) {
                g_rsql_statement.enum_width = 2u;
            } else return syntax(&parser);
            if (!punctuation(&parser, '(')) return syntax(&parser);
            for (;;) {
                if (g_rsql_statement.enum_member_count >=
                    RSQL_ENUM_MEMBERS_MAX) return syntax(&parser);
                index = g_rsql_statement.enum_member_count;
                if (!name(&parser, g_rsql_statement.enum_members[index],
                          RSQL_COLUMN_NAME_MAX)) return syntax(&parser);
                enum_value = index;
                if (punctuation(&parser, '=')) {
                    if (!number(&parser, &enum_value)) return syntax(&parser);
                }
                g_rsql_statement.enum_values[index] = enum_value;
                ++g_rsql_statement.enum_member_count;
                if (punctuation(&parser, ')')) break;
                if (!punctuation(&parser, ',')) return syntax(&parser);
            }
        } else if (!temporary && keyword(&parser, "INDEX")) {
            g_rsql_statement.kind = RSQL_STMT_CREATE_INDEX;
            if (!name(&parser, g_rsql_statement.index_name,
                      RSQL_TABLE_NAME_MAX) || !keyword(&parser, "ON") ||
                !name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX) || !punctuation(&parser, '(')) {
                return syntax(&parser);
            }
            for (;;) {
                if (g_rsql_statement.column_count >=
                    RSQL_TABLE_COLUMNS_MAX) return syntax(&parser);
                if (!name(&parser,
                        g_rsql_statement.columns[
                            g_rsql_statement.column_count].name,
                        RSQL_COLUMN_NAME_MAX)) return syntax(&parser);
                ++g_rsql_statement.column_count;
                if (punctuation(&parser, ')')) break;
                if (!punctuation(&parser, ',')) return syntax(&parser);
            }
        } else return syntax(&parser);
    } else if (keyword(&parser, "DROP")) {
        if (keyword(&parser, "TABLE")) {
            g_rsql_statement.kind = RSQL_STMT_DROP_TABLE;
            if (!name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        } else if (keyword(&parser, "INDEX")) {
            g_rsql_statement.kind = RSQL_STMT_DROP_INDEX;
            if (!name(&parser, g_rsql_statement.index_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        } else if (keyword(&parser, "TYPE")) {
            g_rsql_statement.kind = RSQL_STMT_DROP_ENUM;
            if (!name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        } else return syntax(&parser);
    } else if (keyword(&parser, "SHOW")) {
        if (keyword(&parser, "DATABASE")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_DATABASE;
        } else if (keyword(&parser, "TABLES")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_TABLES;
        } else if (keyword(&parser, "COLUMNS")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_COLUMNS;
            if (!keyword(&parser, "FROM") ||
                !name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        } else if (keyword(&parser, "INDEXES")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_INDEXES;
        } else if (keyword(&parser, "TYPES")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_TYPES;
        } else if (keyword(&parser, "MEMBERS")) {
            g_rsql_statement.kind = RSQL_STMT_SHOW_MEMBERS;
            if (!keyword(&parser, "FROM") ||
                !name(&parser, g_rsql_statement.table_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        } else return syntax(&parser);
    } else if (keyword(&parser, "INSERT")) {
        if (!keyword(&parser, "INTO")) return syntax(&parser);
        g_rsql_statement.kind = RSQL_STMT_INSERT;
        if (!name(&parser, g_rsql_statement.table_name,
                  RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        if (!keyword(&parser, "VALUES") || !punctuation(&parser, '(')) {
            return syntax(&parser);
        }
        for (;;) {
            if (g_rsql_statement.value_count >= RSQL_TABLE_COLUMNS_MAX) {
                return syntax(&parser);
            }
            if (!parse_value(&parser,
                    &g_rsql_statement.values[g_rsql_statement.value_count])) {
                return syntax(&parser);
            }
            ++g_rsql_statement.value_count;
            if (punctuation(&parser, ')')) break;
            if (!punctuation(&parser, ',')) return syntax(&parser);
        }
    } else if (keyword(&parser, "DELETE")) {
        if (!keyword(&parser, "FROM")) return syntax(&parser);
        g_rsql_statement.kind = RSQL_STMT_DELETE;
        if (!name(&parser, g_rsql_statement.table_name,
                  RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        if (keyword(&parser, "WHERE")) {
            g_rsql_statement.where_present = 1u;
            if (!parse_bool_or(&parser)) return syntax(&parser);
        }
    } else if (keyword(&parser, "UPDATE")) {
        g_rsql_statement.kind = RSQL_STMT_UPDATE;
        if (!name(&parser, g_rsql_statement.table_name,
                  RSQL_TABLE_NAME_MAX) || !keyword(&parser, "SET")) {
            return syntax(&parser);
        }
        for (;;) {
            if (g_rsql_statement.column_count >= RSQL_TABLE_COLUMNS_MAX) {
                return syntax(&parser);
            }
            if (!name(&parser,
                    g_rsql_statement.columns[
                        g_rsql_statement.column_count].name,
                    RSQL_COLUMN_NAME_MAX) || !punctuation(&parser, '=') ||
                !parse_value(&parser,
                    &g_rsql_statement.values[
                        g_rsql_statement.column_count])) {
                return syntax(&parser);
            }
            ++g_rsql_statement.column_count;
            if (!punctuation(&parser, ',')) break;
        }
        if (keyword(&parser, "WHERE")) {
            g_rsql_statement.where_present = 1u;
            if (!parse_bool_or(&parser)) return syntax(&parser);
        }
    } else if (keyword(&parser, "SELECT")) {
        g_rsql_statement.kind = RSQL_STMT_SELECT;
        if (keyword(&parser, "DISTINCT")) g_rsql_statement.distinct = 1u;
        if (punctuation(&parser, '*')) {
            g_rsql_statement.select_mode = RSQL_SELECT_SCAN;
            g_rsql_statement.select_all = 1u;
        } else {
            for (;;) {
                if (g_rsql_statement.projection_count >=
                    RSQL_TABLE_COLUMNS_MAX) return syntax(&parser);
                if (!parse_select_item(&parser,
                        g_rsql_statement.projection_count)) {
                    return syntax(&parser);
                }
                ++g_rsql_statement.projection_count;
                if (!punctuation(&parser, ',')) break;
            }
        }
        if (!keyword(&parser, "FROM") ||
            !name(&parser, g_rsql_statement.table_name,
                  RSQL_TABLE_NAME_MAX)) return syntax(&parser);
        if (keyword(&parser, "AS") &&
            !name(&parser, g_rsql_statement.table_alias,
                  RSQL_COLUMN_NAME_MAX)) return syntax(&parser);
        if (!parse_index_hint(&parser, g_rsql_statement.index_name, 1u)) {
            return syntax(&parser);
        }
        if (keyword(&parser, "CROSS")) {
            if (!keyword(&parser, "JOIN")) return syntax(&parser);
            g_rsql_statement.join_type = RSQL_JOIN_CROSS;
        } else if (keyword(&parser, "INNER")) {
            if (!keyword(&parser, "JOIN")) return syntax(&parser);
            g_rsql_statement.join_type = RSQL_JOIN_INNER;
        } else if (keyword(&parser, "LEFT")) {
            keyword(&parser, "OUTER");
            if (!keyword(&parser, "JOIN")) return syntax(&parser);
            g_rsql_statement.join_type = RSQL_JOIN_LEFT;
        } else if (keyword(&parser, "JOIN")) {
            g_rsql_statement.join_type = RSQL_JOIN_INNER;
        }
        if (g_rsql_statement.join_type != RSQL_JOIN_NONE) {
            if (!name(&parser, g_rsql_statement.join_table_name,
                      RSQL_TABLE_NAME_MAX)) return syntax(&parser);
            if (keyword(&parser, "AS") &&
                !name(&parser, g_rsql_statement.join_table_alias,
                      RSQL_COLUMN_NAME_MAX)) return syntax(&parser);
            if (!parse_index_hint(&parser,
                    g_rsql_statement.columns[6].type_name, 2u)) {
                return syntax(&parser);
            }
            if (g_rsql_statement.join_type != RSQL_JOIN_CROSS) {
                if (!keyword(&parser, "ON") ||
                    !parse_bool_or(&parser)) return syntax(&parser);
                g_rsql_statement.join_predicate_count =
                    g_rsql_statement.predicate_count;
                g_rsql_statement.join_bool_program_count =
                    g_rsql_statement.bool_program_count;
            }
            if (keyword(&parser, "CROSS")) {
                if (!keyword(&parser, "JOIN")) return syntax(&parser);
                g_rsql_statement.subquery_compare_op = RSQL_JOIN_CROSS;
            } else if (keyword(&parser, "INNER")) {
                if (!keyword(&parser, "JOIN")) return syntax(&parser);
                g_rsql_statement.subquery_compare_op = RSQL_JOIN_INNER;
            } else if (keyword(&parser, "LEFT")) {
                keyword(&parser, "OUTER");
                if (!keyword(&parser, "JOIN")) return syntax(&parser);
                g_rsql_statement.subquery_compare_op = RSQL_JOIN_LEFT;
            } else if (keyword(&parser, "JOIN")) {
                g_rsql_statement.subquery_compare_op = RSQL_JOIN_INNER;
            }
            if (g_rsql_statement.subquery_compare_op != RSQL_JOIN_NONE) {
                g_rsql_statement.subquery_kind = RSQL_SUBQUERY_WIDE_JOIN;
                if (!name(&parser, g_rsql_statement.subquery_table_name,
                          RSQL_TABLE_NAME_MAX)) return syntax(&parser);
                if (keyword(&parser, "AS") &&
                    !name(&parser, g_rsql_statement.subquery_table_alias,
                          RSQL_COLUMN_NAME_MAX)) return syntax(&parser);
                if (!parse_index_hint(&parser,
                        g_rsql_statement.columns[7].type_name, 4u)) {
                    return syntax(&parser);
                }
                if (g_rsql_statement.subquery_compare_op != RSQL_JOIN_CROSS &&
                    (!keyword(&parser, "ON") ||
                     !parse_subquery_bool_or(&parser))) {
                    return syntax(&parser);
                }
            }
        }
        if (keyword(&parser, "WHERE")) {
            g_rsql_statement.where_present = 1u;
            if (!parse_bool_or(&parser)) return syntax(&parser);
        }
        if (keyword(&parser, "GROUP")) {
            char group_name[RSQL_COLUMN_NAME_MAX + 1u];
            if (!keyword(&parser, "BY")) return syntax(&parser);
            for (;;) {
                if (g_rsql_statement.group_count >=
                    RSQL_TABLE_COLUMNS_MAX) return syntax(&parser);
                if (!qualified_name(&parser, group_name) ||
                    !store_aggregate_group_name(
                        g_rsql_statement.group_count, group_name)) {
                    return syntax(&parser);
                }
                ++g_rsql_statement.group_count;
                if (!punctuation(&parser, ',')) break;
            }
        }
        if (keyword(&parser, "ORDER")) {
            if (!keyword(&parser, "BY")) return syntax(&parser);
            for (;;) {
                if (g_rsql_statement.order_count >=
                    RSQL_TABLE_COLUMNS_MAX) {
                    return syntax(&parser);
                }
                if (number(&parser, &enum_value)) {
                    if (enum_value == 0u ||
                        enum_value > g_rsql_statement.projection_count) {
                        return syntax(&parser);
                    }
                    g_rsql_statement.enum_members[
                        g_rsql_statement.order_count][0] =
                            RSQL_ORDER_PROJECTION_MARKER;
                    g_rsql_statement.enum_members[
                        g_rsql_statement.order_count][1] =
                            (char)(enum_value - 1u);
                    g_rsql_statement.enum_members[
                        g_rsql_statement.order_count][2] = '\0';
                } else if (!qualified_name(&parser,
                        g_rsql_statement.enum_members[
                            g_rsql_statement.order_count])) {
                    return syntax(&parser);
                }
                if (keyword(&parser, "DESC")) {
                    g_rsql_statement.order_desc_mask |=
                        ordinal_mask(g_rsql_statement.order_count);
                } else keyword(&parser, "ASC");
                ++g_rsql_statement.order_count;
                if (!punctuation(&parser, ',')) break;
            }
        }
        if (g_scalar_literal_pool_start <
            (rsql_u16)(g_rsql_statement.order_count *
                       sizeof(g_rsql_statement.enum_members[0])) ||
            (g_rsql_statement.subquery_kind == RSQL_SUBQUERY_WIDE_JOIN &&
             g_rsql_statement.using_index &&
             g_scalar_literal_pool_start < 15u)) {
            return syntax(&parser);
        }
        if (keyword(&parser, "LIMIT")) {
            g_rsql_statement.limit_present = 1u;
            if (!number(&parser, &g_rsql_statement.limit)) {
                return syntax(&parser);
            }
        }
        if (keyword(&parser, "OFFSET")) {
            if (!number(&parser, &g_rsql_statement.offset)) {
                return syntax(&parser);
            }
            if (!g_rsql_statement.limit_present && keyword(&parser, "LIMIT")) {
                g_rsql_statement.limit_present = 1u;
                if (!number(&parser, &g_rsql_statement.limit)) {
                    return syntax(&parser);
                }
            }
        }
        g_rsql_statement.select_mode = RSQL_SELECT_SCAN;
        if (g_rsql_statement.group_count != 0u) {
            g_rsql_statement.select_mode = RSQL_SELECT_AGGREGATE;
        }
        for (index = 0u; index < g_rsql_statement.projection_count; ++index) {
            if (RSQL_PROJECTION_IS_SCALAR(
                    g_rsql_statement.projection_aggregate[index])) {
                g_rsql_statement.limit_present |=
                    RSQL_RESULT_SCALAR_PRESENT;
            }
            if (g_rsql_statement.projection_aggregate[index] != RSQL_AGG_NONE &&
                g_rsql_statement.projection_aggregate[index] <= RSQL_AGG_MAX) {
                g_rsql_statement.select_mode = RSQL_SELECT_AGGREGATE;
            }
        }
    } else return RSQL_ERR_UNSUPPORTED_SQL;
    skip_space(&parser);
    if (parser.offset < parser.length && parser.sql[parser.offset] == ';') {
        ++parser.offset;
        skip_space(&parser);
    }
    if (parser.offset != parser.length) return syntax(&parser);
    return RSQL_OK;
}
