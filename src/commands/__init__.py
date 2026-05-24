"""
Code Analyzer command-line tools.

Each command can be run independently:

    python3 -m src.commands.explainer_command    <owner/repo> <pr_number>
    python3 -m src.commands.auditor_command      <owner/repo> <pr_number>
    python3 -m src.commands.designer_command     <owner/repo> <pr_number> [design-doc]
    python3 -m src.commands.orchestrator_command <owner/repo> <pr_number> [design-doc]

Test mode — use a local diff file, no live PR needed:

    python3 -m src.commands.explainer_command    <owner/repo> --test [diff-file]
    python3 -m src.commands.auditor_command      <owner/repo> --test [diff-file]
    python3 -m src.commands.designer_command     <owner/repo> --test [diff-file] [design-doc]
    python3 -m src.commands.orchestrator_command <owner/repo> --test [diff-file] [design-doc]
"""

# Lazy imports to avoid RuntimeWarning when submodules are run with python3 -m
__all__ = ["explainer", "auditor", "designer", "orchestrator"]


def explainer():
    from .explainer_command import main
    main()


def auditor():
    from .auditor_command import main
    main()


def designer():
    from .designer_command import main
    main()


def orchestrator():
    from .orchestrator_command import main
    main()
