"""
conftest.py - Pytest configuration and fixtures for SSV-Video v2.1 tests

Provides shared fixtures and configuration for all test modules.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.error_handler import SSVVideoError, APIError, ValidationError
from utils.logger import setup_logger
from utils.validator import APIProvider


@pytest.fixture
def temp_dir():
    """Temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'ai': {
            'provider': 'openai_gpt',
            'model': 'gpt-4',
            'language': 'ru',
            'temperature': 0.7
        },
        'output': {
            'directory': 'output',
            'format': 'json'
        }
    }


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_transcript():
    """Sample video transcript for testing"""
    return """
    Добро пожаловать на наш канал. Сегодня мы будем говорить о важной теме.
    Это видео содержит полезную информацию для всех зрителей.
    Мы рассмотрим несколько ключевых аспектов данной темы.
    """ * 10  # Make it longer for realistic testing


@pytest.fixture
def test_logger(temp_dir):
    """Test logger instance"""
    log_file = os.path.join(temp_dir, 'test.log')
    return setup_logger('test_logger', log_file)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_api_credentials():
    """Mock API credentials"""
    return {
        'provider': APIProvider.OPENAI_GPT,
        'api_key': 'sk-test-key-1234567890abcdef'
    }


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


# Test helpers
class TestHelpers:
    """Helper functions for tests"""
    
    @staticmethod
    def create_mock_video_metadata():
        """Create mock video metadata"""
        return {
            'title': 'Test Video Title',
            'description': 'Test description',
            'tags': ['test', 'video', 'sample'],
            'chapters': ['00:00 - Intro', '01:00 - Main content']
        }
    
    @staticmethod
    def assert_valid_title(title: str):
        """Assert title is valid"""
        assert isinstance(title, str)
        assert 0 < len(title) <= 100
        assert title.strip() == title
    
    @staticmethod
    def assert_valid_description(description: str):
        """Assert description is valid"""
        assert isinstance(description, str)
        assert len(description) > 0
    
    @staticmethod
    def assert_valid_tags(tags: list):
        """Assert tags are valid"""
        assert isinstance(tags, list)
        assert len(tags) > 0
        assert all(isinstance(tag, str) for tag in tags)


@pytest.fixture
def test_helpers():
    """Test helper instance"""
    return TestHelpers()
