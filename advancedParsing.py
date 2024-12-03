import re
from typing import List, Dict, Any, Optional
import logging

class AdvancedMappingParser:
    def __init__(self):
        # Set up logging
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _parse_condition_block(self, block: str) -> Dict[str, Any]:
        """
        Enhanced parsing for complex condition blocks with multiple parsing strategies
        """
        # Remove any leading 'If' or 'When' and trim
        block = re.sub(r'^(If|When)\s*', '', block, flags=re.IGNORECASE).strip()

        # Special handling for NUMBER type with multiple conditions
        number_conditions = [
            # Patterns for scale-based conditions
            (r'scale is (.*?):(.+)', self._parse_scale_condition),
            # Patterns for precision-based conditions
            (r'precision (.*?):(.+)', self._parse_precision_condition),
            # Catch-all for other complex conditions
            (r'(.*):(.+)', self._parse_generic_condition)
        ]

        for pattern, handler in number_conditions:
            match = re.search(pattern, block, re.IGNORECASE | re.DOTALL)
            if match:
                parsed = handler(match)
                if parsed:
                    return parsed

        # Fallback for simpler conditions
        simple_match = re.match(r'(.*?)\s*:\s*(.+)', block)
        if simple_match:
            return {
                "raw_condition": simple_match.group(1).strip(),
                "type": simple_match.group(2).strip()
            }

        return None

    def _find_best_target_type(self, source_mapping: Dict[str, Any], target_mappings: List[Dict[str, Any]]) -> str:
        """
        Match the replicate type in source_mapping with the target type from target_mappings.
        """
        replicate_type = source_mapping.get('type', 'N/A').lower()

        for target_entry in target_mappings:
            source_type = target_entry.get('source_or_replicate_type', '').lower()
            if replicate_type == source_type:
                return target_entry.get('replicate_or_target_type', 'N/A')

        self.logger.warning(f"No match found for replicate type: {replicate_type}")
        return 'N/A'

    def _parse_scale_condition(self, match) -> Optional[Dict[str, Any]]:
        """
        Parse conditions related to scale
        """
        condition = match.group(1).strip()
        target_type = match.group(2).strip()

        # Advanced scale condition parsing
        if 'is < 0' in condition:
            return {
                "condition_type": "scale",
                "scale_condition": "less_than_zero",
                "type": target_type
            }
        elif 'is 0' in condition:
            return {
                "condition_type": "scale",
                "scale_condition": "zero",
                "type": target_type
            }

        return None

    def _parse_precision_condition(self, match) -> Optional[Dict[str, Any]]:
        """
        Parse conditions related to precision
        """
        condition = match.group(1).strip()
        target_type = match.group(2).strip()

        # Parsing various precision conditions
        precision_patterns = [
            (r'= 0', 'zero', 'REAL8'),
            (r'<= 2', 'less_or_equal_2', 'INT1'),
            (r'> 2 and <= 4', 'between_2_and_4', 'INT2'),
            (r'> 4 and <= 9', 'between_4_and_9', 'INT4'),
            (r'> 9', 'greater_than_9', 'NUMERIC')
        ]

        for pattern, description, default_type in precision_patterns:
            if re.search(pattern, condition):
                return {
                    "condition_type": "precision",
                    "precision_condition": description,
                    "type": target_type or default_type
                }

        return None

    def _parse_generic_condition(self, match) -> Optional[Dict[str, Any]]:
        """
        Parse generic catch-all conditions
        """
        condition = match.group(1).strip()
        target_type = match.group(2).strip()

        # Handle variations like "all other cases", "default", etc.
        if condition.lower() in ['all other cases', 'default', 'otherwise']:
            return {
                "condition_type": "default",
                "type": target_type
            }

        return None

    def parse_complex_mapping(self, replicate_type: str) -> List[Dict[str, Any]]:
        """
        Parse replicate types with advanced condition handling.
        """
        # Simple types that don't need complex parsing
        SIMPLE_TYPES = {
            "INT4", "INT2", "INT8", "REAL4", "REAL8", "NCLOB", "BLOB", "DATETIME",
            "DATE", "TIME", "STRING", "CLOB", "BOOLEAN", "NUMERIC", "UINT1",
            "WSTRING", "BYTES", "INT1", "UINT2", "UINT4", "UINT8", "IGNORED",
            "NOT SUPPORTED", "FLOAT", "DOUBLE", "INT", "LONG", "TIMESTAMP",
            "TINYINT", "SMALLINT", "BIGINT", "BOOL", "FLOAT4", "FLOAT8",
            "NUMBER", "BYTEA", "INTEGER", "TEXT", "REAL", "BIT", "BYTEINT",
            "XMLTYPE", "IMAGE", "UNITEXT"
        }

        # Normalize input
        replicate_type = replicate_type.strip()

        # Check for simple types first
        if replicate_type in SIMPLE_TYPES:
            return [{"type": replicate_type, "condition": None}]

        # Handle conditional mappings
        parsed_entries = []

        # Split by lines and handle each line
        lines = replicate_type.split("\n")
        current_condition = None

        for line in lines:
            line = line.strip()

            # Check for condition lines
            if line.startswith("If ") or line.startswith("When ") or ":" in line:
                # Extract condition
                condition_match = re.match(r'^(If|When)\s*(.*?):\s*(.+)', line)
                if condition_match:
                    current_condition = condition_match.group(2).strip()
                    line = condition_match.group(3).strip()
                else:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_condition = parts[0].strip()
                        line = parts[1].strip()

            # Extract type and any additional details
            type_match = re.match(r'^(\w+)(\s*\(.*\))?', line)
            if type_match:
                base_type = type_match.group(1)
                details = type_match.group(2) if type_match.group(2) else ""

                # Verify base type is valid
                if base_type in SIMPLE_TYPES:
                    parsed_entry = {
                        "type": base_type + (details if details else ""),
                        "condition": current_condition
                    }
                    parsed_entries.append(parsed_entry)

        # Fallback for completely unmatched types
        if not parsed_entries:
            parsed_entries.append({
                "type": replicate_type,
                "condition": None
            })

        return parsed_entries


def process_database_mappings(source_data, target_data):
    """
    Process database type mappings with advanced handling.
    """
    parser = AdvancedMappingParser()
    combined_data = []

    for source_entry in source_data.get('data_types', []):
        source_type = source_entry.get('source_or_replicate_type', 'Unknown Source Type')
        replicate_type = source_entry.get('replicate_or_target_type', 'N/A')

        # Parse replicate types, handling conditions if necessary
        parsed_mappings = parser.parse_complex_mapping(replicate_type)

        for mapping in parsed_mappings:
            # Use the full replicate type from the original mapping
            replicate_type_clean = clean_replicate_type(mapping.get('type', 'N/A'))

            # Find corresponding target type
            target_entries = target_data.get('data_types', [])
            target_match = next((
                entry.get('replicate_or_target_type', 'N/A')
                for entry in target_entries
                if clean_replicate_type(entry.get('source_or_replicate_type', '')) == replicate_type_clean
            ), 'N/A')

            # Construct the combined row
            combined_row = {
                "source_type": f"{source_type} ({mapping['condition']})" if mapping['condition'] else source_type,
                "replicate_type": replicate_type_clean,
                "target_type": target_match
            }

            combined_data.append(combined_row)

    return combined_data




def clean_replicate_type(replicate_type: str) -> str:
    """
    Remove details like (n), (p,s), or (fraction) from replicate types.
    Preserve the base type.
    """
    # Strip parentheses while keeping the base type
    return re.sub(r'\(.*?\)', '', replicate_type).strip()

def extract_replicate_details(replicate_type: str) -> str:
    """
    Extract details like (n), (p,s), or (fraction) from replicate types.
    """
    match = re.search(r'\((.*?)\)', replicate_type)
    return f"({match.group(1)})" if match else ""

def clean_lob_type(target_type: str) -> str:
    """
    Remove length/p/s conditions for LOB datatypes.
    """
    if "LOB" in target_type.upper():
        return target_type.split("(")[0].strip()  # Strip conditions
    if "CLOB" in target_type.upper():
        return target_type.split("(")[0].strip()  # Strip conditions
    return target_type

