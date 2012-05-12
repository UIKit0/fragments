import sys, os, pdb

from fragman import __version__, FragmanError
from fragman.config import FragmanConfig, configuration_directory_name, find_configuration, ConfigurationFileNotFound, ConfigurationDirectoryNotFound

class ExecutionError(FragmanError): pass

def help(*a):
    """Prints help."""
    return "help!"


def init(*a):
    """Initialize a fragments repository."""
    try:
        config = FragmanConfig()
    except ConfigurationFileNotFound, exc:
        config = FragmanConfig(autoload=False)
        config.dump()
    except ConfigurationDirectoryNotFound, exc:
        configuration_parent = os.path.split(os.getcwd())[0]
        if os.access(configuration_parent, os.R_OK|os.W_OK):
            configuration_path = os.path.join(configuration_parent, configuration_directory_name)
            os.mkdir(configuration_path)
            config = FragmanConfig(configuration_path, autoload=False)
            config.dump()
        else:
            raise ExecutionError("Could not create fragments directory in %r, aborting.\n(Do you have the correct permissions?)" % configuration_parent)
    else:
        raise ExecutionError("Current fragments configuration found in %r, aborting." % config.path)
    return "Fragments configuration created in %r" % config.path


def stat(*a):
    config = FragmanConfig()
    return repr(config)


if __name__ == '__main__':
    print "%s version %s.%s.%s" % ((__package__,) + __version__)
    if len(sys.argv) > 1:
        try:
            print(locals().get(sys.argv[1], help)(sys.argv[2:]))
        except ExecutionError, exc:
            sys.exit(exc.message)
    else:
        print(help())