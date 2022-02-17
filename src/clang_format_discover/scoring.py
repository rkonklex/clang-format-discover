import xml.sax
import xml.sax.handler
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .config import StyleSettings, inline_clang_format_config
from .utils import chunkify


ProcessArgsList = List[str]
LineIterable = Iterable[str]
ProcessDispatcher = Callable[[Iterable[ProcessArgsList]], Iterable[LineIterable]]


def eval_clang_format_cost(
        file_list: List[str],
        dispatcher: ProcessDispatcher,
        config: Optional[StyleSettings] = None,
        batch_max: int = 10
        ) -> int:
    if config is None:
        style_arg = '--style=file'
    else:
        style_arg = '--style=' + inline_clang_format_config(config)
    def make_clang_format_args(files: Iterable[str]) -> List[str]:
        return ['clang-format', '--output-replacements-xml', style_arg, *files]

    handler = ReplacementsXmlHandler()
    parser = xml.sax.make_parser(['xml.sax.IncrementalParser'])
    parser.setContentHandler(handler)

    file_list_chunks = chunkify(file_list, batch_max)
    for output_xml in dispatcher(map(make_clang_format_args, file_list_chunks)):
        for line in output_xml:
            if line.startswith("<?xml version='1.0'?>"):
                parser.close()
                parser.reset()
            parser.feed(line)

    return handler.get_total_cost()


class ReplacementsXmlHandler(xml.sax.handler.ContentHandler):
    _started: bool = False
    _num_remove: int
    _num_insert: int
    _replacements: List[Tuple[int, int]]

    def __init__(self) -> None:
        super().__init__()
        self._replacements = []

    def startElement(self, name: str, attrs: Dict[str, str]):
        if name == 'replacement':
            self._started = True
            self._num_remove = int(attrs.get('length', 0))
            self._num_insert = 0

    def characters(self, content: str):
        if self._started:
            self._num_insert += len(content)

    def endElement(self, name: str):
        if self._started:
            self._replacements.append((self._num_remove, self._num_insert))
            self._started = False

    def get_total_cost(self):
        return sum(ninsert + nremove for ninsert, nremove in self._replacements)
