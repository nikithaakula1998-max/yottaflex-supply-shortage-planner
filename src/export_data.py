"""Stream YottaFlex CSV datasets to JSONL and a queryable SQLite database.

Run: py -m src.export_data --input outputs/streaming_full_02
"""
import argparse
import csv
import json
import sqlite3
from pathlib import Path

DATASETS = (
    'sku', 'location', 'supplier', 'supplier_capacity', 'lead_time',
    'inventory', 'forecast_demand', 'purchase_order', 'production_capacity',
    'production_plan', 'bom', 'shortage', 'mitigation_option', 'ground_truth',
)

# Known numeric columns. All identifiers, dates, weeks and statuses remain text.
INTEGER_COLUMNS = {
    'lead_days', 'quantity', 'on_hand', 'weekly_capacity', 'moq',
    'max_production_units', 'planned_quantity', 'opening_balance', 'inbound',
    'demand', 'projected_balance', 'shortage_qty', 'quantity_per_unit',
}
REAL_COLUMNS = {'unit_cost', 'estimated_cost', 'priority_score'}


def sql_type(name):
    if name in INTEGER_COLUMNS:
        return 'INTEGER'
    if name in REAL_COLUMNS:
        return 'REAL'
    return 'TEXT'


def convert(name, value):
    if value == '':
        return None
    if name in INTEGER_COLUMNS:
        try:
            return int(value)
        except ValueError:
            return float(value)
    if name in REAL_COLUMNS:
        return float(value)
    return value


def quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def export(input_folder, output_folder, batch_size=10000):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    db_path = output_folder / 'yottaflex.sqlite3'
    schema_path = output_folder / 'schema.sql'
    if db_path.exists():
        raise FileExistsError(f'{db_path} already exists; move or remove it before rerunning')

    conn = sqlite3.connect(db_path)
    statements = []
    counts = {}
    try:
        for dataset in DATASETS:
            csv_path = input_folder / f'{dataset}.csv'
            if not csv_path.is_file():
                raise FileNotFoundError(csv_path)
            with csv_path.open('r', newline='', encoding='utf-8-sig') as source:
                reader = csv.DictReader(source)
                columns = reader.fieldnames
                if not columns:
                    raise ValueError(f'CSV has no header: {csv_path}')
                definitions = ', '.join(f'{quote(col)} {sql_type(col)}' for col in columns)
                create = f'CREATE TABLE {quote(dataset)} ({definitions});'
                statements.append(create)
                conn.execute(create)
                placeholders = ', '.join('?' for _ in columns)
                insert = f'INSERT INTO {quote(dataset)} VALUES ({placeholders})'
                count = 0
                batch = []
                jsonl_path = output_folder / f'{dataset}.jsonl'
                with jsonl_path.open('w', encoding='utf-8', newline='\n') as json_out:
                    for row in reader:
                        record = {col: convert(col, row[col]) for col in columns}
                        json_out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
                        batch.append(tuple(record[col] for col in columns))
                        count += 1
                        if len(batch) >= batch_size:
                            conn.executemany(insert, batch)
                            batch.clear()
                    if batch:
                        conn.executemany(insert, batch)
                conn.commit()
                counts[dataset] = count
                print(f'{dataset}: {count:,} records exported', flush=True)
        # Index commonly joined identifiers without changing source data.
        indexes = (
            ('sku', 'sku_id'), ('location', 'location_id'),
            ('supplier', 'supplier_id'), ('shortage', 'shortage_id'),
            ('mitigation_option', 'shortage_id'),
            ('forecast_demand', 'sku_id'), ('purchase_order', 'supplier_id'),
            ('production_plan', 'sku_id'), ('inventory', 'sku_id'),
        )
        for table, column in indexes:
            name = f'idx_{table}_{column}'
            statement = f'CREATE INDEX {quote(name)} ON {quote(table)} ({quote(column)});'
            conn.execute(statement)
            statements.append(statement)
        conn.commit()
        schema_path.write_text('\n'.join(statements) + '\n', encoding='utf-8')
        (output_folder / 'export_counts.json').write_text(
            json.dumps(counts, indent=2) + '\n', encoding='utf-8'
        )
        print(f'Export complete. SQLite: {db_path}')
        print(f'SQL schema: {schema_path}')
        print('JSONL files: 14')
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Export synthetic CSV datasets to JSONL and SQLite')
    parser.add_argument('--input', default='outputs/streaming_full_02')
    parser.add_argument('--out', default=None)
    args = parser.parse_args()
    export(args.input, args.out or str(Path(args.input) / 'exports'))


if __name__ == '__main__':
    main()
