#!/usr/bin/env python
"""Scala klucze z plików źródłowych z katalogami `openapi-docs_<lang>.properties` (zadanie 192).

    python merge_catalogs.py KATALOG_DOCELOWY [--replace-prefix schema.] pl=PLIK en=PLIK de=PLIK ...

Dla każdego języka klucze z pliku źródłowego są dopisywane do `KATALOG_DOCELOWY/openapi-docs_<lang>.properties`. Klucz istniejący
zostaje nadpisany nową wartością. Z `--replace-prefix` najpierw usuwane są z katalogu docelowego wszystkie klucze o podanym
przedrostku (odświeżenie całej grupy, np. `schema.` po zmianie Javadoc), a dopiero potem dopisywane nowe. Wynik jest posortowany po
kluczach, zapisany w UTF-8 (surowe znaki) z końcami linii LF.

Typowe katalogi docelowe: `mercury/mercury-ws-app-rest-generator/src/main/resources/META-INF/mercury`.
"""
import argparse
import io
import sys


def read_lines(path):
    return [line for line in io.open(path, encoding='utf-8').read().replace('\r\n', '\n').split('\n') if line]


def key_of(line):
    return line.split('=', 1)[0]


def merge(target, source, replace_prefix):
    merged = {}
    removed = 0
    for line in read_lines(target):
        if replace_prefix and key_of(line).startswith(replace_prefix):
            removed += 1
            continue
        merged[key_of(line)] = line
    added = 0
    for line in read_lines(source):
        added += key_of(line) not in merged
        merged[key_of(line)] = line
    io.open(target, 'w', encoding='utf-8', newline='\n').write('\n'.join(merged[k] for k in sorted(merged)) + '\n')
    return removed, added, len(merged)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('target_dir')
    parser.add_argument('--replace-prefix', default=None)
    parser.add_argument('sources', nargs='+', help='kod_języka=plik_źródłowy')
    args = parser.parse_args()
    for pair in args.sources:
        lang, _, source = pair.partition('=')
        if not source:
            parser.error('oczekiwano kod_języka=plik, dostałem: ' + pair)
        target = '%s/openapi-docs_%s.properties' % (args.target_dir.rstrip('/'), lang)
        removed, added, total = merge(target, source, args.replace_prefix)
        print('%s: usunięte %d, dodane %d, razem %d' % (lang, removed, added, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
