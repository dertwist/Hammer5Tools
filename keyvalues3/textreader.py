import parsimonious
import keyvalues3 as kv3
import uuid
import itertools

common = """
    data = (value / value_flagged)

    array = "[" items "]"
        items = (ws* data ws* ",")* ws* (data ws*)?
    dict = "{" ws* pair* "}"
        pair = key ws* "=" ws* data ws*
            key = (identifier / quoted_string)

    # TODO: only one flag
    value_flagged = (flags ":") value
        flags = (identifier "|")* identifier
    value = null / true / false / number / multiline_string / quoted_string / dict / array / binary_blob
        null = "null"
        true = "true"
        false = "false"
        number = ~r"[+-]?" (~r"(((?>\\d+[\\.](?>\\d+)?)|(?>(?>\\d+)?[\\.]\\d+))|\\d+)([Ee][+-]?(?1))?" / ~r"nan"i / ~r"inf"i)
        quoted_string = ~r'"(?:[^"\\\\]|\\\\.)*"'
        #quoted_string_old_no_escaped = ~r'"[^"]*"'
    
        multiline_string = ~r'\"{3}\\r?\\n(.*?)\\"{3}'us
        binary_blob = '#[' ws* (~r'[A-F0-9a-f]{2}' ws*)* ']'

    ws = ~r"\\s+" / single_line_comment / multi_line_comment
    single_line_comment = ~r"//.*?\\n"
    multi_line_comment = ~r"/\\*[^*]*\\*+(?:[^/*][^*]*\\*+)*/"

    identifier = ~r"[a-zA-Z0-9_.]+"i
    """

kv3grammar = parsimonious.Grammar(
    """
    kv3 = header ws* data ws* # TODO: null needs whitespace after header but object doesnt
    header = "<!--" ws+ "kv3" ws+ encoding ws+ format ws+ "-->"
        encoding = "encoding:" identifier ":version" guid
        format = "format:" identifier ":version" guid
            guid = ~r"{[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}}"i
    """ + common
)

kv3grammar_noheader = parsimonious.Grammar(
    """
    kv3_noheader = ws* data ws*
    """ + common
)

class KV3TextReader(parsimonious.NodeVisitor):
    grammar = kv3grammar
    unwrapped_exceptions: tuple[type[BaseException], ...] = (ValueError,)
    class list_of_nodes(list):
        pass
    class NonObject(object):
        def __bool__(self):
            return False

    non_object = NonObject()

    def parse(self, text: str) -> kv3.KV3File:
        """Parse the given text into a KV3File object."""
        try:
            return super().parse(text)
        except parsimonious.exceptions.ParseError as e:
            raise kv3.KV3DecodeError("KV3 Text " + str(e)) from e
    loads = parse
    read = parse

    def visit(self, node) -> kv3.KV3File:
        return super().visit(node)

    @staticmethod
    def is_object(node):
        return node is not KV3TextReader.non_object and not isinstance(node, KV3TextReader.list_of_nodes)

    def visit_kv3(self, node, visited_children: list[kv3.KV3Header | kv3.ValueType]) -> kv3.KV3File:
        header = visited_children[0]
        if not isinstance(header, kv3.KV3Header):
            raise ValueError("kv3 has invalid header")
        try:
            data = next(data for data in visited_children[1:] if self.is_object(data))
        except StopIteration:
            raise ValueError("kv3 contains no data")
        else:
            return kv3.KV3File(value=data, format=header.format, original_encoding=header.encoding)

    def visit_header(self, _, visited_children) -> kv3.KV3Header:
        return kv3.KV3Header(encoding=visited_children[4], format=visited_children[6])

    def visit_encoding(self, _, visited_children) -> kv3.Encoding:
        return kv3.Encoding(name=visited_children[1].text, version=uuid.UUID(visited_children[3].text))
    def visit_format(self, _, visited_children) -> kv3.Format:
        return kv3.Format(name=visited_children[1].text, version=uuid.UUID(visited_children[3].text))

    def visit_data(self, node, visited_children) -> kv3.ValueType:
        return visited_children[0]

    def visit_value(self, _, visited_children) -> kv3.ValueType:
        return visited_children[0]

    def visit_value_flagged(self, _, visited_children) -> kv3.flagged_value:
        return kv3.flagged_value(value=visited_children[1], flags=visited_children[0][0])

    def visit_flags(self, _, visited_children) -> kv3.Flag:
        flag = kv3.Flag(0)
        try:
            if isinstance(visited_children[0], KV3TextReader.list_of_nodes):
                for child in visited_children[0]:
                    flag |= kv3.Flag[child[0].text.lower()]
            return flag | kv3.Flag[visited_children[1].text.lower()]
        except KeyError as e:
            raise ValueError(f"Invalid flag {e.args[0]!r}") from e

    def visit_null(self, *_): return None
    def visit_true(self, *_): return True
    def visit_false(self, *_): return False
    def visit_number(self, node, _) -> int | float:
        sign, number = node
        sign = sign.text if sign else ""
        # number is anyof(regexnode)
        groups = number.children[0].match.groups()
        if not len(groups):
            # nan or inf
            return float(sign + number.text)
        if groups[2] is not None:
            # scientific notation
            return float(sign + groups[0] + groups[2].split('.')[0])
        if groups[1] is None:
            # no decimal point
            return int(sign + groups[0])
        return float(sign + groups[0])

    def visit_quoted_string(self, node, _): return node.text[1:-1].encode('raw_unicode_escape').decode('unicode_escape')
    def visit_multiline_string(self, node, _):
        return kv3.flagged_value(node.match.group(1), kv3.Flag.multilinestring)
    #def visit_binary_blob(self, node, visited_children): return bytes.fromhex(node.text[2:-1])

    def visit_array(self, node, visited_children) -> list:
        return visited_children[1]

    def visit_items(self, node, visited_children) -> list:
        rv = []
        items_comma = visited_children[0] if isinstance(visited_children[0], KV3TextReader.list_of_nodes) else []
        item_no_comma = visited_children[2] if isinstance(visited_children[2], KV3TextReader.list_of_nodes) else []
        for child in itertools.chain(items_comma, item_no_comma):
            if child is None:
                continue
            it = (item for item in child if self.is_object(item))
            rv.append(next(it))
        return rv

    def visit_binary_blob(self, node, _) -> bytearray:
        return bytearray.fromhex(node.children[2].text)

    def visit_dict(self, node, visited_children) -> dict:
        rv = {}
        pairs = visited_children[2]
        if pairs is self.non_object:
            return rv
        for kvp in pairs:
            rv[kvp[0]] = kvp[1]
        return rv

    def visit_pair(self, node, visited_children) -> tuple[str, None | object | kv3.flagged_value]:
        it = (child for child in visited_children if self.is_object(child))
        return next(it), next(it)

    def visit_key(self, node, maybe_quoted_string: list_of_nodes) -> str:
        # str or RegexNode
        if isinstance(maybe_quoted_string[0], str):
            return maybe_quoted_string[0]
        return node.text

    def generic_visit(self, node, visited_children):
        """ The generic visit method. """
        if node.expr_name == 'ws':
            return None
        if len(visited_children):
            return KV3TextReader.list_of_nodes(visited_children)
        return node if node.expr_name else KV3TextReader.non_object

class KV3TextReaderNoHeader(KV3TextReader):
    grammar = kv3grammar_noheader
    def visit_kv3_noheader(self, node, visited_children: list[kv3.ValueType]) -> kv3.ValueType:
        try:
            data = next(data for data in visited_children if self.is_object(data))
        except StopIteration:
            raise ValueError("kv3 contains no data")
        else:
            return data
