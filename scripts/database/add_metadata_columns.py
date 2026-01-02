#!/usr/bin/env python3
"""
Add metadata columns to all climate data tables
Tracks whether data is real (EDGAR), estimated, or synthetic
"""

import duckdb
from pathlib import Path
from datetime import datetime

class MetadataColumnAdder:
    """Add metadata tracking columns to all tables"""

    def __init__(self, db_path="data/warehouse/climategpt.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self.log_file = open("metadata_migration.log", "w")
        self.stats = {
            'tables_modified': 0,
            'columns_added': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def log(self, message: str, level: str = "INFO"):
        """Log messages"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {level}: {message}"
        print(log_msg)
        self.log_file.write(log_msg + "\n")
        self.log_file.flush()

    def get_all_tables(self):
        """Get all emission tables from database"""
        try:
            result = self.conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()
            tables = [row[0] for row in result if any(
                sector in row[0] for sector in [
                    'transport', 'power', 'agriculture', 'waste',
                    'buildings', 'fuel_exploitation', 'industrial_combustion', 'industrial_processes'
                ]
            )]
            return sorted(tables)
        except Exception as e:
            self.log(f"Error getting tables: {e}", "ERROR")
            return []

    def add_metadata_columns(self, table_name: str) -> bool:
        """Add metadata columns to a table"""
        try:
            columns_to_add = [
                ("data_type", "VARCHAR", "Type of data: real, estimated, or synthesized"),
                ("data_origin", "VARCHAR", "Origin: EDGAR, IEA, WB, Statistical, Synthetic"),
                ("quality_flag", "VARCHAR", "Quality level: HIGH, MEDIUM, LOW"),
                ("estimation_method", "VARCHAR", "Method if estimated: statistical, interpolation, regional_scaling"),
                ("confidence_score", "DOUBLE", "Confidence 0.0-1.0: 1.0=verified, 0.5=estimated, 0.2=synthetic"),
                ("synthetic_probability", "DOUBLE", "Probability data is synthetic: 0.0-1.0"),
                ("estimation_notes", "VARCHAR", "Notes about estimation or synthesis")
            ]

            for col_name, col_type, description in columns_to_add:
                try:
                    # Check if column already exists
                    self.conn.execute(f"SELECT {col_name} FROM {table_name} LIMIT 1")
                    self.log(f"  Column '{col_name}' already exists in {table_name}", "SKIP")
                except Exception:
                    # Column doesn't exist, add it
                    sql = f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN {col_name} {col_type};
                    """
                    self.conn.execute(sql)
                    self.stats['columns_added'] += 1
                    self.log(f"  ✓ Added column '{col_name}' to {table_name}", "SUCCESS")

            self.stats['tables_modified'] += 1
            return True

        except Exception as e:
            self.log(f"Error adding columns to {table_name}: {e}", "ERROR")
            self.stats['errors'] += 1
            return False

    def set_default_values(self, table_name: str) -> bool:
        """Set default values based on table origin"""
        try:
            # Determine if table is from real EDGAR data or estimated
            # For now, all are marked as 'real' (from EDGAR baseline)
            # Later phases will update specific regions to 'estimated' or 'synthesized'

            sql = f"""
            UPDATE {table_name}
            SET
                data_type = 'real',
                data_origin = 'EDGAR v2024',
                quality_flag = 'HIGH',
                estimation_method = NULL,
                confidence_score = 0.95,
                synthetic_probability = 0.0,
                estimation_notes = 'EDGAR verified data'
            WHERE data_type IS NULL;
            """

            self.conn.execute(sql)
            self.log(f"  ✓ Set defaults for {table_name}", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"Error setting defaults for {table_name}: {e}", "ERROR")
            self.stats['errors'] += 1
            return False

    def run_migration(self):
        """Execute full migration"""
        self.log("\n" + "="*80, "INFO")
        self.log("METADATA COLUMN MIGRATION - START", "PHASE_START")
        self.log("="*80, "INFO")

        tables = self.get_all_tables()
        self.log(f"Found {len(tables)} climate data tables to update\n", "INFO")

        # Step 1: Add columns to all tables
        self.log("STEP 1: Adding metadata columns to all tables...", "STEP")
        for i, table in enumerate(tables, 1):
            self.log(f"\n[{i}/{len(tables)}] Processing: {table}", "INFO")
            self.add_metadata_columns(table)

        # Step 2: Set default values
        self.log("\n" + "-"*80, "INFO")
        self.log("STEP 2: Setting default values for all tables...", "STEP")
        for i, table in enumerate(tables, 1):
            self.log(f"\n[{i}/{len(tables)}] Setting defaults: {table}", "INFO")
            self.set_default_values(table)

        # Summary
        self.log("\n" + "="*80, "INFO")
        self.log("MIGRATION COMPLETE", "PHASE_COMPLETE")
        self.log("="*80, "INFO")
        self.log(f"Tables modified: {self.stats['tables_modified']}", "SUMMARY")
        self.log(f"Columns added: {self.stats['columns_added']}", "SUMMARY")
        self.log(f"Errors: {self.stats['errors']}", "SUMMARY")

        duration = datetime.now() - self.stats['start_time']
        self.log(f"Duration: {duration.total_seconds():.1f} seconds", "SUMMARY")

        self.log("\nNEXT STEPS:", "INFO")
        self.log("1. Run populate_estimated_data.py to mark estimated/synthesized records", "INFO")
        self.log("2. Update MCP server to return metadata in responses", "INFO")
        self.log("3. Update run_llm.py to display data type in answers", "INFO")

        self.conn.close()
        self.log_file.close()

if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/warehouse/climategpt.duckdb"

    migrator = MetadataColumnAdder(db_path)
    migrator.run_migration()
