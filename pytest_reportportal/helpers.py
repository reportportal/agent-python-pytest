"""This module includes help functions for both plugin and service modules."""
import logging

log = logging.getLogger(__name__)


def get_attributes(rp_attributes):
    """Generate list of attributes for RP.

    :param list rp_attributes: rp_attributes option value
    :return list:                     List of dictionaries to be passed to the
                                      RP Python client
    """
    attrs = []
    for rp_attr in rp_attributes:
        try:
            key, value = rp_attr.split(':')
            attr_dict = {'key': key, 'value': value}
        except ValueError:
            attr_dict = {'value': rp_attr}

        if all(value for value in attr_dict.values()):
            attrs.append(attr_dict)
            continue
        log.debug('Failed to process "{0}" attribute, attribute value'
                  ' should not be empty.'.format(rp_attr))
    return attrs
