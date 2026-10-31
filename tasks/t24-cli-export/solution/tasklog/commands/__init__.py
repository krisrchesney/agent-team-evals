from . import add, backup, done, export, list_, show, stats

# Every command module defines NAME, HELP, configure(parser) and run(args, con, store, clock).
COMMANDS = [add, list_, show, done, stats, backup, export]
