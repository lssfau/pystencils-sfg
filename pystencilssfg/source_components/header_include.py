from __future__ import annotations

class SfgHeaderInclude:
    def __init__(self, header_file: str, system_header : bool = False, private: bool = False):
        self._header_file = header_file
        self._system_header = system_header
        self._private = private

    @property
    def system_header(self):
        return self._system_header
    
    @property
    def private(self):
        return self._private

    def get_code(self):
        if self._system_header:
            return f"#include <{self._header_file}>"
        else:
            return f'#include "{self._header_file}"'
        
    def __hash__(self) -> int:
        return hash((self._header_file, self._system_header, self._private))
    
    def __eq__(self, other: SfgHeaderInclude) -> bool:
        return (isinstance(other, SfgHeaderInclude) 
                and self._header_file == other._header_file
                and self._system_header == other._system_header
                and self._private == other._private)
