from cvsslib import cvss3, cvss2
from cvsslib.utils import get_enums, run_calc


class VectorError(Exception):
    def __init__(self, message):
        self.message = message


def detect_vector(vector):
    if vector.startswith("CVSS:3.0"):
        module = cvss3
    else:
        module = cvss2

    return module


def sorted_vector(vector):
    replaced = False
    if vector.startswith("CVSS:3.0/"):
        vector = vector.replace("CVSS:3.0/", "")
        replaced = True

    vector = "/".join(sorted(vector.split("/")))

    if replaced:
        vector = "CVSS:3.0/" + vector

    return vector


def to_vector(module, getter):
    vectors = []

    for name, enum in get_enums(module):
        enum_attr = getter(enum)
        vector = enum_attr.get_options()["vector"]

        key = enum_attr.get_value_key()

        if key is None:
            continue

        vectors.append("{0}:{1}".format(vector, key))

    res = "/".join(sorted(vectors))
    if module is cvss3:
        res = "CVSS:3.0/" + res

    return res


def calculate_vector(vector, module):
    vector_values = parse_vector(vector, module)

    def _getter(enum_type):
        if enum_type not in vector_values:
            ret = enum_type.get_default()
        else:
            ret = vector_values[enum_type]

        return ret

    return run_calc(module.calculate, getter=_getter)


def parse_vector(vector, module=None):
    if module is None:
        module = detect_vector(vector)

    vector_map, vector_values = {}, {}
    mandatory_keys, given_keys = set(), set()

    for name, enum in get_enums(module):
        options = enum.get_options()
        vector_name = options["vector"]

        vector_map[vector_name] = enum
        if options.get("mandatory", "") == "yes":
            mandatory_keys.add(vector_name)

    split_vector = vector.split("/")

    for part in split_vector:
        if not part:
            continue

        key, value = part.split(":")

        if key == "CVSS":
            continue  # CVSS3 is prefixed with CVSS:3.0/

        if key not in vector_map:
            raise VectorError("Unknown key {0} in {1} vector".format(key, module.__name__))

        enum = vector_map[key]
        try:
            value_from_key = enum.get_value_from_vector_key(value)
        except RuntimeError as e:
            raise VectorError(*e.args)
        vector_values[enum] = value_from_key
        given_keys.add(key)

    required_diff = mandatory_keys.difference(given_keys)

    if required_diff:
        raise VectorError("Missing mandatory keys {0}".format(required_diff))

    return vector_values
