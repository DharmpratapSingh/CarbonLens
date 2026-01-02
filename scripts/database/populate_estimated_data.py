#!/usr/bin/env python3
"""
Populate estimated/synthesized data markers
Identifies which records are estimated vs real EDGAR data
"""

import duckdb
from datetime import datetime

class EstimatedDataMarker:
    """Mark estimated and synthesized data records"""

    def __init__(self, db_path="data/warehouse/climategpt.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self.log_file = open("estimated_data_marking.log", "w")
        self.stats = {
            'real_records': 0,
            'estimated_records': 0,
            'synthesized_records': 0,
            'total_updates': 0,
            'errors': 0
        }

    def log(self, message: str, level: str = "INFO"):
        """Log messages"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {level}: {message}"
        print(log_msg)
        self.log_file.write(log_msg + "\n")
        self.log_file.flush()

    def mark_estimated_regions(self):
        """Mark data from estimated regions as 'estimated'"""
        self.log("\n" + "="*80, "INFO")
        self.log("MARKING ESTIMATED DATA REGIONS", "PHASE_START")
        self.log("="*80, "INFO")

        # Regions with estimated/synthesized data (from master_implementation.py)
        estimated_regions = {
            'africa': {
                'countries': ['Algeria', 'Angola', 'Benin', 'Botswana', 'Burkina Faso',
                             'Burundi', 'Cameroon', 'Cape Verde', 'Central African Republic',
                             'Chad', 'Comoros', 'Congo', 'Cote d\'Ivoire', 'Democratic Republic',
                             'Djibouti', 'Egypt', 'Equatorial Guinea', 'Eritrea', 'Eswatini',
                             'Ethiopia', 'Gabon', 'Gambia', 'Ghana', 'Guinea', 'Guinea-Bissau',
                             'Kenya', 'Lesotho', 'Liberia', 'Libya', 'Madagascar', 'Malawi',
                             'Mali', 'Mauritania', 'Mauritius', 'Morocco', 'Mozambique',
                             'Namibia', 'Niger', 'Nigeria', 'Rwanda', 'Sao Tome', 'Senegal',
                             'Seychelles', 'Sierra Leone', 'Somalia', 'South Africa', 'South Sudan',
                             'Sudan', 'Tanzania', 'Togo', 'Tunisia', 'Uganda', 'Zambia', 'Zimbabwe'],
                'data_type': 'estimated',
                'quality_flag': 'MEDIUM',
                'confidence_score': 0.60,
                'synthetic_probability': 0.30,
                'estimation_method': 'regional_scaling',
                'estimation_notes': 'Estimated from regional averages and UN statistics'
            },
            'middle_east_central_asia': {
                'countries': ['Afghanistan', 'Armenia', 'Azerbaijan', 'Bahrain', 'Georgia',
                             'Iran', 'Iraq', 'Israel', 'Jordan', 'Kazakhstan', 'Kuwait',
                             'Kyrgyzstan', 'Lebanon', 'Oman', 'Palestine', 'Qatar',
                             'Saudi Arabia', 'Syria', 'Tajikistan', 'Turkey', 'Turkmenistan',
                             'United Arab Emirates', 'Uzbekistan', 'Yemen'],
                'data_type': 'estimated',
                'quality_flag': 'MEDIUM',
                'confidence_score': 0.65,
                'synthetic_probability': 0.25,
                'estimation_method': 'statistical_model',
                'estimation_notes': 'Estimated from energy production statistics'
            },
            'small_islands': {
                'countries': ['Antigua and Barbuda', 'Bahamas', 'Barbados', 'Belize',
                             'Cabo Verde', 'Comoros', 'Cyprus', 'Dominica', 'Fiji',
                             'Grenada', 'Guam', 'Jamaica', 'Kiribati', 'Malta', 'Mauritius',
                             'Nauru', 'Palau', 'Puerto Rico', 'Samoa', 'Sao Tome and Principe',
                             'Seychelles', 'Solomon Islands', 'St. Kitts and Nevis',
                             'St. Lucia', 'St. Vincent and the Grenadines', 'Tonga', 'Trinidad and Tobago',
                             'Tuvalu', 'Vanuatu'],
                'data_type': 'synthesized',
                'quality_flag': 'LOW',
                'confidence_score': 0.40,
                'synthetic_probability': 0.90,
                'estimation_method': 'random_generation',
                'estimation_notes': 'Synthetic data generated from global patterns (limited real data)'
            }
        }

        sectors = ['transport', 'power', 'agriculture', 'waste', 'buildings',
                   'fuel_exploitation', 'industrial_combustion', 'industrial_processes']

        for sector in sectors:
            self.log(f"\nProcessing {sector} sector...", "INFO")

            for region_name, region_info in estimated_regions.items():
                countries = region_info['countries']
                # Properly escape single quotes in country names for SQL
                escaped_countries = [c.replace("'", "''") for c in countries]
                countries_str = "', '".join(escaped_countries)

                for granularity in ['country_year', 'admin1_year', 'city_year',
                                   'country_month', 'admin1_month', 'city_month']:
                    table_name = f"{sector}_{granularity}"

                    try:
                        # Check if table exists
                        self.conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")

                        # Update records for this region
                        sql = f"""
                        UPDATE {table_name}
                        SET
                            data_type = '{region_info['data_type']}',
                            quality_flag = '{region_info['quality_flag']}',
                            confidence_score = {region_info['confidence_score']},
                            synthetic_probability = {region_info['synthetic_probability']},
                            estimation_method = '{region_info['estimation_method']}',
                            estimation_notes = '{region_info['estimation_notes']}'
                        WHERE country_name IN ('{countries_str}')
                          AND data_type = 'real'
                          AND data_origin = 'EDGAR v2024';
                        """

                        self.conn.execute(sql)

                        # Count affected rows
                        count_result = self.conn.execute(
                            f"SELECT COUNT(*) FROM {table_name} WHERE data_type = '{region_info['data_type']}'"
                        ).fetchone()

                        if count_result and count_result[0] > 0:
                            self.log(f"  ✓ {table_name}: {count_result[0]} records marked as {region_info['data_type']}",
                                   "SUCCESS")
                            self.stats['total_updates'] += count_result[0]

                            if region_info['data_type'] == 'estimated':
                                self.stats['estimated_records'] += count_result[0]
                            elif region_info['data_type'] == 'synthesized':
                                self.stats['synthesized_records'] += count_result[0]

                    except Exception as e:
                        self.log(f"  ⚠️ {table_name}: {str(e)}", "WARNING")
                        self.stats['errors'] += 1

    def generate_statistics(self):
        """Generate statistics on data types"""
        self.log("\n" + "="*80, "INFO")
        self.log("DATA TYPE STATISTICS", "PHASE_START")
        self.log("="*80, "INFO")

        sectors = ['transport', 'power', 'agriculture', 'waste', 'buildings',
                   'fuel_exploitation', 'industrial_combustion', 'industrial_processes']

        for sector in sectors:
            self.log(f"\n{sector.upper()} SECTOR:", "INFO")

            table_name = f"{sector}_country_year"
            try:
                # Count by data type
                result = self.conn.execute(f"""
                    SELECT
                        data_type,
                        COUNT(*) as count,
                        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table_name}), 1) as percentage
                    FROM {table_name}
                    GROUP BY data_type
                    ORDER BY count DESC
                """).fetchall()

                for row in result:
                    data_type, count, percentage = row
                    self.log(f"  {data_type}: {count} records ({percentage}%)", "INFO")

                # Average confidence by data type
                result = self.conn.execute(f"""
                    SELECT
                        data_type,
                        ROUND(AVG(confidence_score), 2) as avg_confidence
                    FROM {table_name}
                    GROUP BY data_type
                    ORDER BY avg_confidence DESC
                """).fetchall()

                self.log(f"  Confidence scores:", "INFO")
                for row in result:
                    data_type, avg_conf = row
                    self.log(f"    {data_type}: {avg_conf}", "INFO")

            except Exception as e:
                self.log(f"  Error generating stats: {e}", "ERROR")

    def run_population(self):
        """Execute full population"""
        self.log("\n" + "="*80, "INFO")
        self.log("ESTIMATED DATA POPULATION - START", "PHASE_START")
        self.log("="*80, "INFO")

        self.mark_estimated_regions()
        self.generate_statistics()

        # Summary
        self.log("\n" + "="*80, "INFO")
        self.log("POPULATION COMPLETE", "PHASE_COMPLETE")
        self.log("="*80, "INFO")
        self.log(f"Total records updated: {self.stats['total_updates']}", "SUMMARY")
        self.log(f"Real records: {self.stats['real_records']}", "SUMMARY")
        self.log(f"Estimated records: {self.stats['estimated_records']}", "SUMMARY")
        self.log(f"Synthesized records: {self.stats['synthesized_records']}", "SUMMARY")
        self.log(f"Errors: {self.stats['errors']}", "SUMMARY")

        self.log("\nNEXT STEPS:", "INFO")
        self.log("1. Update MCP server to return metadata in responses", "INFO")
        self.log("2. Update run_llm.py to display data type in answers", "INFO")
        self.log("3. Test with queries to verify data type flags", "INFO")

        self.conn.close()
        self.log_file.close()

if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/warehouse/climategpt.duckdb"

    marker = EstimatedDataMarker(db_path)
    marker.run_population()
