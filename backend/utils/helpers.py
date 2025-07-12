"""
Utility helper functions for Alert RCA Management System
"""

import json
import logging
import hashlib
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from email.utils import parseaddr
import unicodedata

logger = logging.getLogger(__name__)


# =============================================================================
# DATETIME UTILITIES
# =============================================================================

def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def format_timestamp(dt: Optional[datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime for display
    
    Args:
        dt: Datetime object to format
        format_str: Format string for strftime
        
    Returns:
        Formatted datetime string or "N/A" if dt is None
    """
    if dt is None:
        return "N/A"
    
    # Convert to UTC if timezone-aware
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse timestamp string to datetime object
    
    Args:
        timestamp_str: Timestamp string in various formats
        
    Returns:
        Datetime object or None if parsing fails
    """
    if not timestamp_str:
        return None
    
    # Common timestamp formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp_str.replace('Z', ''), fmt.replace('Z', ''))
        except ValueError:
            continue
    
    logger.warning(f"Failed to parse timestamp: {timestamp_str}")
    return None


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time difference from now
    
    Args:
        dt: Datetime to compare
        
    Returns:
        Human-readable time difference (e.g., "2 hours ago")
    """
    if dt is None:
        return "Unknown"
    
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    return "Just now"


# =============================================================================
# JSON UTILITIES
# =============================================================================

def safe_json_loads(json_str: Union[str, None], default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Safely load JSON string with default fallback
    
    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON dict or default value
    """
    if default is None:
        default = {}
    
    if not json_str:
        return default
    
    try:
        result = json.loads(json_str)
        return result if isinstance(result, dict) else default
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse JSON: {json_str[:100]}... Error: {e}")
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely dump data to JSON string
    
    Args:
        data: Data to serialize
        default: Default value if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Failed to serialize JSON: {e}")
        return default


def merge_json_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple JSON dictionaries
    
    Args:
        *dicts: Variable number of dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result


# =============================================================================
# STRING UTILITIES
# =============================================================================

def clean_string(text: str, max_length: int = None) -> str:
    """
    Clean and normalize string
    
    Args:
        text: String to clean
        max_length: Maximum length to truncate to
        
    Returns:
        Cleaned string
    """
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', str(text))
    
    # Remove control characters
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
    
    # Strip whitespace
    text = text.strip()
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def slugify(text: str) -> str:
    """
    Convert string to URL-friendly slug
    
    Args:
        text: Text to convert
        
    Returns:
        URL-friendly slug
    """
    if not text:
        return ""
    
    # Convert to lowercase and normalize
    text = unicodedata.normalize('NFKD', str(text).lower())
    
    # Remove non-alphanumeric characters and replace with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def extract_keywords(text: str, min_length: int = 3, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text
    
    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keywords
    """
    if not text:
        return []
    
    # Simple keyword extraction
    words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + ',}\b', text.lower())
    
    # Common stop words to filter out
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'throughout', 'despite',
        'towards', 'upon', 'concerning', 'regarding', 'without', 'within'
    }
    
    # Filter out stop words and get unique keywords
    keywords = list(set(word for word in words if word not in stop_words))
    
    # Sort by length (longer keywords first) and limit
    keywords.sort(key=len, reverse=True)
    
    return keywords[:max_keywords]


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def is_valid_email(email: str) -> bool:
    """
    Validate email address
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email
    """
    if not email:
        return False
    
    try:
        name, addr = parseaddr(email)
        return '@' in addr and '.' in addr.split('@')[1]
    except Exception:
        return False


def is_valid_uuid(uuid_str: str) -> bool:
    """
    Validate UUID string
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        True if valid UUID
    """
    try:
        uuid.UUID(uuid_str)
        return True
    except (ValueError, TypeError):
        return False


def validate_severity(severity: str) -> bool:
    """
    Validate alert severity level
    
    Args:
        severity: Severity level to validate
        
    Returns:
        True if valid severity
    """
    valid_severities = ['critical', 'high', 'medium', 'low']
    return severity.lower() in valid_severities


def validate_status(status: str, valid_statuses: List[str]) -> bool:
    """
    Validate status against allowed values
    
    Args:
        status: Status to validate
        valid_statuses: List of valid status values
        
    Returns:
        True if valid status
    """
    return status.lower() in [s.lower() for s in valid_statuses]


# =============================================================================
# ID GENERATION UTILITIES
# =============================================================================

def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate unique ID with optional prefix
    
    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part
        
    Returns:
        Unique ID string
    """
    random_part = uuid.uuid4().hex[:length]
    return f"{prefix}_{random_part}" if prefix else random_part


def generate_hash(text: str, algorithm: str = 'md5') -> str:
    """
    Generate hash from text
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')
        
    Returns:
        Hash string
    """
    if not text:
        return ""
    
    text_bytes = text.encode('utf-8')
    
    if algorithm == 'md5':
        return hashlib.md5(text_bytes).hexdigest()
    elif algorithm == 'sha1':
        return hashlib.sha1(text_bytes).hexdigest()
    elif algorithm == 'sha256':
        return hashlib.sha256(text_bytes).hexdigest()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")


# =============================================================================
# DATA TRANSFORMATION UTILITIES
# =============================================================================

def normalize_metric_name(metric_name: str) -> str:
    """
    Normalize metric name for consistency
    
    Args:
        metric_name: Original metric name
        
    Returns:
        Normalized metric name
    """
    if not metric_name:
        return ""
    
    # Convert to lowercase and replace special characters
    normalized = re.sub(r'[^a-z0-9_]', '_', metric_name.lower())
    
    # Remove multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def extract_numeric_value(value: Union[str, int, float]) -> Optional[float]:
    """
    Extract numeric value from various input types
    
    Args:
        value: Input value to extract number from
        
    Returns:
        Numeric value or None if extraction fails
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove common units and formatting
        cleaned = re.sub(r'[^\d.-]', '', value)
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    return None


def flatten_dict(d: Dict[str, Any], separator: str = '.', prefix: str = '') -> Dict[str, Any]:
    """
    Flatten nested dictionary
    
    Args:
        d: Dictionary to flatten
        separator: Separator for nested keys
        prefix: Prefix for keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for k, v in d.items():
        new_key = f"{prefix}{separator}{k}" if prefix else k
        
        if isinstance(v, dict):
            items.extend(flatten_dict(v, separator, new_key).items())
        else:
            items.append((new_key, v))
    
    return dict(items)


# =============================================================================
# ERROR HANDLING UTILITIES
# =============================================================================

def safe_divide(a: Union[int, float], b: Union[int, float], default: float = 0.0) -> float:
    """
    Safely divide two numbers
    
    Args:
        a: Numerator
        b: Denominator
        default: Default value if division fails
        
    Returns:
        Division result or default value
    """
    try:
        if b == 0:
            return default
        return float(a) / float(b)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None, 
                     level: int = logging.DEBUG) -> None:
    """
    Log function call with arguments
    
    Args:
        func_name: Name of the function
        args: Function arguments
        kwargs: Function keyword arguments
        level: Logging level
    """
    args_str = ", ".join(str(arg) for arg in (args or []))
    kwargs_str = ", ".join(f"{k}={v}" for k, v in (kwargs or {}).items())
    
    all_args = ", ".join(filter(None, [args_str, kwargs_str]))
    log_msg = f"Calling {func_name}({all_args})"
    
    logger.log(level, log_msg)


def log_execution_time(func_name: str, start_time: datetime, 
                      level: int = logging.INFO) -> None:
    """
    Log function execution time
    
    Args:
        func_name: Name of the function
        start_time: Function start time
        level: Logging level
    """
    execution_time = (utc_now() - start_time).total_seconds()
    logger.log(level, f"{func_name} executed in {execution_time:.3f} seconds")


# =============================================================================
# BUSINESS LOGIC HELPERS
# =============================================================================

def calculate_severity_score(severity: str) -> int:
    """
    Convert severity to numeric score for comparison
    
    Args:
        severity: Severity level string
        
    Returns:
        Numeric severity score
    """
    severity_map = {
        'critical': 4,
        'high': 3,
        'medium': 2,
        'low': 1
    }
    return severity_map.get(severity.lower(), 0)


def get_higher_severity(severity1: str, severity2: str) -> str:
    """
    Get the higher of two severity levels
    
    Args:
        severity1: First severity level
        severity2: Second severity level
        
    Returns:
        Higher severity level
    """
    score1 = calculate_severity_score(severity1)
    score2 = calculate_severity_score(severity2)
    
    if score1 >= score2:
        return severity1.lower()
    else:
        return severity2.lower()


def extract_system_name(source_system: str) -> str:
    """
    Extract clean system name from source system string
    
    Args:
        source_system: Original source system string
        
    Returns:
        Clean system name
    """
    if not source_system:
        return "unknown"
    
    # Remove common prefixes/suffixes and normalize
    cleaned = source_system.lower()
    cleaned = re.sub(r'(monitoring|system|service|alert)[-_]?', '', cleaned)
    cleaned = re.sub(r'[-_](monitoring|system|service|alert)', '', cleaned)
    cleaned = re.sub(r'[^a-z0-9]', '', cleaned)
    
    return cleaned or "unknown"


def parse_metric_threshold(threshold_str: str) -> Optional[Dict[str, Any]]:
    """
    Parse threshold string into structured format
    
    Args:
        threshold_str: Threshold string (e.g., ">85%", "<=100ms")
        
    Returns:
        Parsed threshold dict or None
    """
    if not threshold_str:
        return None
    
    # Common threshold patterns
    patterns = [
        r'([><=!]+)\s*([\d.]+)\s*(%|ms|s|MB|GB|KB)?',
        r'([\d.]+)\s*([><=!]+)\s*([\d.]+)',
        r'between\s+([\d.]+)\s+and\s+([\d.]+)'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, threshold_str.lower())
        if match:
            groups = match.groups()
            return {
                'original': threshold_str,
                'operator': groups[0] if len(groups) > 0 else None,
                'value': safe_float(groups[1]) if len(groups) > 1 else None,
                'unit': groups[2] if len(groups) > 2 else None
            }
    
    return {'original': threshold_str, 'parsed': False}
