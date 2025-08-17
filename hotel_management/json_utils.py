from decimal import Decimal
import json

class DecimalEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that converts Decimal objects to float
    for proper JSON serialization.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def decimal_safe_dumps(obj):
    """
    Helper function to safely serialize objects containing Decimal values to JSON.
    
    Args:
        obj: The object to serialize (can be a dict, list, or any JSON serializable object)
        
    Returns:
        str: JSON string representation of the object with Decimal values converted to float
    """
    return json.dumps(obj, cls=DecimalEncoder)