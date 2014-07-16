# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import json


def normalize_whitespace(s):
    """
    Removes leading and ending whitespace from a string.
    """
    return ' '.join(s.split())


def lowerstr(s):
    """
    Makes everything to a string and tries to make it lower case. Also
    normalizes whitespace.
    """
    return normalize_whitespace(unicode(s).lower())


def update_item_properties(item_properties, new_properties):
    for key, value in new_properties.items():
        fixed_key = key.replace(' ', '_').lower()  # No spaces or caps
        if value or value is 0:
            try:
                # Handle string representations of lists and booleans
                json_value = json.loads(value)
                if type(json_value) is dict:
                    raise ValueError  # Neo4j does not support dictionaries
                item_properties[fixed_key] = json_value
            except (ValueError, TypeError):
                try:
                    item_properties[fixed_key] = normalize_whitespace(value)
                except (TypeError, AttributeError):
                    # if value is not a string we will end up here
                    item_properties[fixed_key] = value
        elif fixed_key in item_properties.keys():
            del item_properties[fixed_key]
    return item_properties


def merge_properties(item_properties, prop_name, new_value):
    """
    Tries to figure out which type of property value that should be merged and
    invoke the right function.
    Returns True if the merge was successful otherwise False.
    """
    existing_value = item_properties.get(prop_name, None)
    if not existing_value:  # A node without existing values for the property
        item_properties[prop_name] = new_value
    else:
        if type(new_value) is int:
            item_properties[prop_name] = existing_value + new_value
        elif type(new_value) is str:
            return False  # Not implemented yet
        elif type(new_value) is list:
            item_properties[prop_name] = merge_list(existing_value, new_value)
        else:
            return False
    return item_properties


def merge_list(existing_value, new_value):
    """
    Takes the name of a property, a list of new property values and the existing
    node values.
    Returns the merged properties.
    """
    new_set = set(existing_value + new_value)
    return list(new_set)