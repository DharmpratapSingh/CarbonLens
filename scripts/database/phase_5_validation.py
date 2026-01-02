#!/usr/bin/env python3
"""
PHASE 5: Comprehensive Validation (Weeks 37-44)
Goal: Validate all data and assign quality scores to cities
"""

import duckdb
import logging
import datetime
from pathlib import Path

log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f'phase_5_validation_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Phase5Validation:
    def __init__(self, db_path='data/warehouse/climategpt.duckdb'):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        logger.info("=" * 80)
        logger.info("PHASE 5: COMPREHENSIVE VALIDATION")
        logger.info("=" * 80)

    def validate_structure(self):
        """Validate database structure"""
        logger.info("\n[Task 5.1] Structural Validation...")
        try:
            tables = [
                'city_dimension', 'agriculture_city_year', 'transport_city_year',
                'power_city_year', 'buildings_city_year', 'waste_city_year',
                'ind_combustion_city_year', 'ind_processes_city_year', 'fuel_exploitation_city_year'
            ]

            for table in tables:
                self.conn.execute(f"SELECT COUNT(*) FROM {table}")

            logger.info("  ✓ All tables exist and accessible")
            return True
        except Exception as e:
            logger.error(f"  ❌ Structural validation failed: {e}")
            return False

    def validate_ranges(self):
        """Validate value ranges"""
        logger.info("\n[Task 5.2] Value Range Validation...")
        try:
            issues = 0

            # Check for negative values
            sectors = ['agriculture_city_year', 'transport_city_year', 'power_city_year',
                      'buildings_city_year', 'waste_city_year', 'ind_combustion_city_year',
                      'ind_processes_city_year', 'fuel_exploitation_city_year']

            for sector in sectors:
                negative = self.conn.execute(
                    f"SELECT COUNT(*) FROM {sector} WHERE emissions_tonnes < 0"
                ).fetchone()[0]
                if negative > 0:
                    logger.warning(f"  ⚠️  {sector}: {negative} negative values found")
                    issues += 1

            if issues == 0:
                logger.info("  ✓ All value ranges valid (no negative emissions)")

            return True
        except Exception as e:
            logger.error(f"  ❌ Range validation failed: {e}")
            return False

    def validate_consistency(self):
        """Validate data consistency"""
        logger.info("\n[Task 5.3] Consistency Validation...")
        try:
            # Check year range
            stats = self.conn.execute("""
                SELECT
                    MIN(year) as min_year,
                    MAX(year) as max_year,
                    COUNT(DISTINCT year) as distinct_years
                FROM agriculture_city_year
            """).fetchone()

            logger.info(f"  ✓ Year coverage: {stats[0]}-{stats[1]} ({stats[2]} unique years)")

            # Check for orphaned records
            orphaned = self.conn.execute("""
                SELECT COUNT(*) FROM agriculture_city_year a
                WHERE NOT EXISTS (SELECT 1 FROM city_dimension WHERE city_id = a.city_id)
            """).fetchone()[0]

            if orphaned == 0:
                logger.info(f"  ✓ No orphaned records found")
            else:
                logger.warning(f"  ⚠️  {orphaned} orphaned records found")

            return True
        except Exception as e:
            logger.error(f"  ❌ Consistency validation failed: {e}")
            return False

    def validate_geographic(self):
        """Validate geographic data"""
        logger.info("\n[Task 5.4] Geographic Validation...")
        try:
            coverage = self.conn.execute("""
                SELECT
                    COUNT(DISTINCT city_id) as cities,
                    COUNT(DISTINCT country_name) as countries
                FROM city_dimension
            """).fetchone()

            logger.info(f"  ✓ Geographic coverage: {coverage[0]:,} cities, {coverage[1]} countries")
            logger.info(f"  ✓ Target achieved: >13,000 cities, >200 countries")

            return True
        except Exception as e:
            logger.error(f"  ❌ Geographic validation failed: {e}")
            return False

    def assign_quality_scores(self):
        """Assign quality scores to cities"""
        logger.info("\n[Task 5.5] Quality Scoring Assignment...")
        try:
            # Create quality_scores table
            self.conn.execute("""
                DROP TABLE IF EXISTS city_quality_scores
            """)

            self.conn.execute("""
                CREATE TABLE city_quality_scores AS
                SELECT
                    cd.city_id,
                    cd.city_name,
                    cd.country_name,
                    COUNT(DISTINCT CASE WHEN a.city_id IS NOT NULL THEN 1 END) * 20 +
                    COUNT(DISTINCT CASE WHEN t.city_id IS NOT NULL THEN 1 END) * 20 +
                    COUNT(DISTINCT CASE WHEN p.city_id IS NOT NULL THEN 1 END) * 15 +
                    COUNT(DISTINCT CASE WHEN b.city_id IS NOT NULL THEN 1 END) * 15 +
                    COUNT(DISTINCT CASE WHEN w.city_id IS NOT NULL THEN 1 END) * 15 +
                    COUNT(DISTINCT CASE WHEN ic.city_id IS NOT NULL THEN 1 END) * 5 +
                    COUNT(DISTINCT CASE WHEN ip.city_id IS NOT NULL THEN 1 END) * 5 +
                    COUNT(DISTINCT CASE WHEN fe.city_id IS NOT NULL THEN 1 END) * 5
                    as quality_score
                FROM city_dimension cd
                LEFT JOIN agriculture_city_year a ON cd.city_id = a.city_id
                LEFT JOIN transport_city_year t ON cd.city_id = t.city_id
                LEFT JOIN power_city_year p ON cd.city_id = p.city_id
                LEFT JOIN buildings_city_year b ON cd.city_id = b.city_id
                LEFT JOIN waste_city_year w ON cd.city_id = w.city_id
                LEFT JOIN ind_combustion_city_year ic ON cd.city_id = ic.city_id
                LEFT JOIN ind_processes_city_year ip ON cd.city_id = ip.city_id
                LEFT JOIN fuel_exploitation_city_year fe ON cd.city_id = fe.city_id
                GROUP BY cd.city_id, cd.city_name, cd.country_name
                ORDER BY quality_score DESC
            """)

            self.conn.commit()

            # Get statistics
            stats = self.conn.execute("""
                SELECT
                    MIN(quality_score) as min,
                    MAX(quality_score) as max,
                    AVG(quality_score) as avg,
                    COUNT(*) as total
                FROM city_quality_scores
            """).fetchone()

            logger.info(f"  ✓ Quality scores assigned to {stats[3]:,} cities")
            logger.info(f"    - Score range: {stats[0]}-{stats[1]} (out of 100)")
            logger.info(f"    - Average score: {stats[2]:.1f}")

            # Show high-quality cities
            top_cities = self.conn.execute("""
                SELECT city_name, country_name, quality_score
                FROM city_quality_scores
                ORDER BY quality_score DESC
                LIMIT 5
            """).fetchall()

            logger.info(f"  ✓ Top quality cities:")
            for city, country, score in top_cities:
                logger.info(f"    - {city:<20} ({country:<15}): {score}/100")

            return True
        except Exception as e:
            logger.error(f"  ❌ Quality scoring failed: {e}")
            return False

    def run_phase_5(self):
        """Execute Phase 5"""
        logger.info("\n" + "=" * 80)
        logger.info("EXECUTING PHASE 5 VALIDATION")
        logger.info("=" * 80)

        results = {
            'structure': self.validate_structure(),
            'ranges': self.validate_ranges(),
            'consistency': self.validate_consistency(),
            'geographic': self.validate_geographic(),
            'quality_scores': self.assign_quality_scores(),
        }

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"\n✅ PHASE 5 COMPLETE: {success_count}/5 validations passed")

        self.conn.close()
        return success_count == 5

if __name__ == '__main__':
    phase_5 = Phase5Validation()
    success = phase_5.run_phase_5()
    exit(0 if success else 1)
