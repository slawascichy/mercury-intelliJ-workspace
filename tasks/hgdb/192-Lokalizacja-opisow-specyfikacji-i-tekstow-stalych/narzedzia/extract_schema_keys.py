#!/usr/bin/env python
"""Wyciąga klucze katalogu opisów schematów i pól z wygenerowanej specyfikacji OpenAPI (zadanie 192, krok 3).

Źródłem opisów jest Javadoc encji i DTO (`schema-docs.json`), który generator `mercury-ws-app-rest-generator` zapisuje
w specyfikacji. To narzędzie zamienia je na klucze katalogu `openapi-docs_<lang>.properties`:

    schema.<Schemat>=opis schematu
    schema.<Schemat>.<pole>=opis pola

Pomijane są: schematy z kropką w nazwie (żądania `XxxRest.YyyRequest` mają opisy z `@WSDLDocumentation`) oraz opis domyślny pola
`id` (klucz `openapi.schema.idDescription`, tekst stały generatora). Wartości są jednoliniowe (nowa linia jako `\\n`).

Użycie (z katalogu repozytorium `mercury`, po zbudowaniu generatora, który odświeża `openapi_pl.json`):

    python extract_schema_keys.py SPECYFIKACJA_PL.json WYJSCIE.properties [--id-description "Unikalny identyfikator instancji obiektu."]

Dalszy ciąg (README.md w tym katalogu): tłumaczenie `localizer.py` i scalenie `merge_catalogs.py`.
"""
import argparse
import io
import json
import sys

BS = chr(92)
ID_DESCRIPTION_PL = 'Unikalny identyfikator instancji obiektu.'


def escape(text):
    """Jednoliniowy zapis wartości w pliku .properties (backslash i nowa linia)."""
    return text.replace(BS, BS + BS).replace('\r', '').replace('\n', BS + 'n')


def extract(spec):
    result = {}
    for name, schema in spec['components']['schemas'].items():
        if '.' in name:
            continue
        description = schema.get('description')
        if isinstance(description, str) and description:
            result['schema.' + name] = description
        for prop, value in (schema.get('properties') or {}).items():
            text = value.get('description') if isinstance(value, dict) else None
            if isinstance(text, str) and text and text != ID_DESCRIPTION_PL:
                result['schema.%s.%s' % (name, prop)] = text
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('spec', help='openapi_pl.json (specyfikacja w języku polskim)')
    parser.add_argument('output', help='plik .properties z kluczami schema.*')
    args = parser.parse_args()
    spec = json.load(io.open(args.spec, encoding='utf-8'))
    keys = extract(spec)
    lines = ['%s=%s' % (k, escape(v)) for k, v in sorted(keys.items())]
    io.open(args.output, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('kluczy %d, unikalnych wartości %d, zapisano %s' % (len(keys), len(set(keys.values())), args.output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
