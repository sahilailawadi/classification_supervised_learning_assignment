"""
Data Source Abstractions for Dual-Mode Architecture.

Provides unified interface for accessing test data from:
- ACADEMIC: Excel files (anonymized data)
- WORK: PostgreSQL database (live production data)

Usage:
    from src.data_source import get_data_source
    
    # Automatically selects based on LLM_MODE
    ds = get_data_source()
    
    # Load test data
    df = ds.load_test_data()
    
    # Get specific test
    test_df = ds.get_test_by_id('LoadTest_001')  # or real ID in work mode
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List
import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BaseDataSource(ABC):
    """Abstract base class for all data sources."""
    
    @abstractmethod
    def load_test_data(self) -> pd.DataFrame:
        """
        Load all test data.
        
        Returns:
            DataFrame with test runs and transactions.
            Expected columns:
            - testplan: Test identifier
            - transaction_name: Transaction/endpoint name
            - exit_code: Test result (1=PASS, 2/3/4=FAIL)
            - num_clients: Number of concurrent users
            - perc_95, perc_99: Percentile response times
            - avg_response_time, min_response_time, max_response_time
            - error_percentage: Error rate
            - txn_requests, txn_failed: Request counts
            - build_version: Build/version identifier
            - And other performance metrics
        """
        pass
    
    @abstractmethod
    def get_test_by_id(self, testplan: str) -> pd.DataFrame:
        """
        Load data for a specific test.
        
        Args:
            testplan: Test plan identifier
            
        Returns:
            DataFrame with transactions for the specified test
        """
        pass
    
    @abstractmethod
    def list_tests(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of available test IDs.
        
        Args:
            limit: Maximum number of test IDs to return
            
        Returns:
            List of testplan identifiers
        """
        pass
    
    def get_mode(self) -> str:
        """Return the data source mode ('academic' or 'work')."""
        return self.__class__.__name__.replace('DataSource', '').lower()


class ExcelDataSource(BaseDataSource):
    """
    Excel-based data source for academic mode.
    
    Reads from anonymized Excel file created by export script.
    """
    
    def __init__(self, excel_path: Optional[Path] = None):
        """
        Initialize Excel data source.
        
        Args:
            excel_path: Path to Excel file. Defaults to academic_demo_data.xlsx
        """
        if excel_path is None:
            project_root = Path(__file__).parent.parent
            excel_path = project_root / 'data_exports' / 'academic_demo_data.xlsx'
        
        self.excel_path = Path(excel_path)
        
        if not self.excel_path.exists():
            raise FileNotFoundError(
                f"Excel file not found: {self.excel_path}\n"
                f"Run: python scripts/export_anonymized_data.py"
            )
        
        # Load data on initialization (it's small enough)
        self._data = None
        self._metadata = None
    
    def _ensure_loaded(self):
        """Lazy load Excel data."""
        if self._data is None:
            print(f"📂 Loading data from {self.excel_path.name}...")
            self._data = pd.read_excel(self.excel_path, sheet_name='test_runs')
            
            # Try to load metadata if it exists
            try:
                self._metadata = pd.read_excel(self.excel_path, sheet_name='metadata')
            except:
                self._metadata = None
            
            print(f"✅ Loaded {len(self._data)} rows, {self._data['testplan'].nunique()} unique tests")
    
    def load_test_data(self) -> pd.DataFrame:
        """Load all test data from Excel."""
        self._ensure_loaded()
        return self._data.copy()
    
    def get_test_by_id(self, testplan: str) -> pd.DataFrame:
        """Load data for a specific test."""
        self._ensure_loaded()
        test_data = self._data[self._data['testplan'] == testplan]
        
        if len(test_data) == 0:
            available = self.list_tests(limit=5)
            raise ValueError(
                f"Test '{testplan}' not found. "
                f"Available tests (first 5): {available}"
            )
        
        return test_data.copy()
    
    def list_tests(self, limit: Optional[int] = None) -> List[str]:
        """Get list of available test IDs."""
        self._ensure_loaded()
        tests = sorted(self._data['testplan'].unique())
        
        if limit:
            tests = tests[:limit]
        
        return tests


class PostgresDataSource(BaseDataSource):
    """
    PostgreSQL-based data source for work mode.
    
    Uses existing extract.py module to query live database.
    """
    
    def __init__(self):
        """Initialize PostgreSQL data source."""
        # Import here to avoid circular dependency
        from src.extract import get_db_engine, extract_training_data
        
        self.get_engine = get_db_engine
        self.extract_function = extract_training_data
        
        # Test connection
        try:
            engine = self.get_engine()
            with engine.connect() as conn:
                # Quick connection test
                result = conn.execute(text("SELECT 1"))
                result.close()
            print("✅ PostgreSQL connection verified")
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to PostgreSQL: {e}\n"
                f"Check your .env file has DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"
            ) from e
    
    def load_test_data(self) -> pd.DataFrame:
        """
        Load test data from PostgreSQL.
        
        Uses the existing extract_training_data() function which applies
        all filters and exclusions.
        """
        print("🔍 Extracting data from PostgreSQL...")
        df = self.extract_function()
        print(f"✅ Loaded {len(df)} rows, {df['testplan'].nunique()} unique tests")
        return df
    
    def get_test_by_id(self, testplan: str) -> pd.DataFrame:
        """
        Load data for a specific test.
        
        Note: This loads all data first, then filters. For production use,
        consider adding a parameterized query to extract.py for efficiency.
        """
        df = self.load_test_data()
        test_data = df[df['testplan'] == testplan]
        
        if len(test_data) == 0:
            available = self.list_tests(limit=5)
            raise ValueError(
                f"Test '{testplan}' not found in database. "
                f"Available tests (first 5): {available}"
            )
        
        return test_data
    
    def list_tests(self, limit: Optional[int] = None) -> List[str]:
        """Get list of available test IDs from database."""
        # Use the same filters as extract_training_data to ensure consistency
        # Quick query matching the extraction logic
        engine = self.get_engine()
        
        query = """
        SELECT DISTINCT tr.testplan
        FROM testrun tr
        INNER JOIN test_summary ts ON ts.testplan = tr.testplan
        WHERE tr.exit_code IS NOT NULL
          AND tr.exit_code != 0
          AND COALESCE(tr.rps_avg, 0) > 0
          AND tr.num_clients = 2000
          AND COALESCE(tr.build_version, '') NOT LIKE 'BAPIS%'
          AND COALESCE(tr.build_version, '') NOT LIKE 'Mercury_DB%'
          AND COALESCE(tr.build_version, '') NOT LIKE 'db_test%'
        ORDER BY tr.testplan DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        with engine.connect() as conn:
            result = pd.read_sql(text(query), conn)
        
        return result['testplan'].tolist()


class DataSourceFactory:
    """
    Factory for creating appropriate data source based on mode.
    
    Mode is determined by LLM_MODE environment variable:
    - "academic": Uses Excel file
    - "work": Uses PostgreSQL database
    """
    
    @staticmethod
    def create_data_source(mode: Optional[str] = None) -> BaseDataSource:
        """
        Create data source based on mode.
        
        Args:
            mode: Override mode ("academic" or "work").
                  If None, reads from LLM_MODE environment variable.
                  
        Returns:
            Configured data source instance
            
        Raises:
            ValueError: If mode is invalid or required config is missing
        """
        mode = mode or os.getenv('LLM_MODE', 'academic')
        mode = mode.lower()
        
        if mode == 'academic':
            print("🎓 Initializing ACADEMIC mode (Excel data source)")
            return ExcelDataSource()
        
        elif mode == 'work':
            print("💼 Initializing WORK mode (PostgreSQL data source)")
            return PostgresDataSource()
        
        else:
            raise ValueError(
                f"Invalid LLM_MODE: '{mode}'. Must be 'academic' or 'work'. "
                f"Set LLM_MODE environment variable."
            )
    
    @staticmethod
    def get_mode() -> str:
        """Get current mode from environment."""
        return os.getenv('LLM_MODE', 'academic').lower()


# Convenience function for getting a data source
def get_data_source(mode: Optional[str] = None) -> BaseDataSource:
    """
    Get configured data source.
    
    Args:
        mode: Override mode ("academic" or "work")
        
    Returns:
        Configured data source
    """
    return DataSourceFactory.create_data_source(mode)
