"""
Shell Module
Runs the app's command strings without a POSIX shell, for Windows (cmd.exe cannot parse `'…'`
quoting or `$(…)`). POSIX systems keep using `shell=True`; see utils.run_cmd / stream_docker_cmd.

The command constants only use a tiny slice of shell syntax, and every argument is quoted with
`shlex.quote`, so `shlex.split` is the exact inverse. Supported on top of that:

  $(cmd)          command substitution, split into words (docker start $(docker ps -aq))
  2>/dev/null     discard the command's stderr
  || true         ignore failure (nothing to do: failures are reported through the output)

Pipes, `&&`, `;` and redirections raise UnsupportedCommand: a new constant that needs them has to
be written without them (or run in Python), never silently mis-parsed.
"""

import re
import shlex
import shutil
import subprocess

from src.utils import platform_utils as plat

_SUBST = re.compile(r"\$\(([^()]*)\)")
_IGNORE_FAILURE = re.compile(r"\s*\|\|\s*true\s*$")
_MARK = re.compile(r"\x00(\d+)\x00")
_OPERATORS = {"|", "||", "&&", ";", "&", ">", ">>", "<"}


class UnsupportedCommand(ValueError):
    """The command uses shell syntax this module deliberately does not emulate."""


def parse(cmd):
    """Split a command string into (argv, discard_stderr), running `$(…)` substitutions."""
    cmd = _IGNORE_FAILURE.sub("", cmd)
    substituted = []

    def capture(match):
        argv, _ = parse(match.group(1))
        try:
            result = subprocess.run(_resolve(argv), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", errors="replace", **plat.popen_flags())
            substituted.append(result.stdout.split())
        except OSError:
            substituted.append([])
        return f"\x00{len(substituted) - 1}\x00"

    argv, discard_stderr = [], False
    for token in shlex.split(_SUBST.sub(capture, cmd)):
        mark = _MARK.fullmatch(token)
        if token == "2>/dev/null":
            discard_stderr = True
        elif mark:
            argv.extend(substituted[int(mark.group(1))])
        elif token in _OPERATORS or re.match(r"\d?>", token):
            raise UnsupportedCommand(f"shell operator {token!r} is not supported here: {cmd}")
        else:
            argv.append(_MARK.sub(lambda m: " ".join(substituted[int(m.group(1))]), token))
    if not argv:
        raise UnsupportedCommand(f"empty command: {cmd}")
    return argv, discard_stderr


def _resolve(argv):
    """Full path of the program (honours PATHEXT, so `trivy` finds trivy.exe / .cmd)."""
    found = shutil.which(argv[0])
    return [found, *argv[1:]] if found else argv


def popen(cmd, **kwargs):
    """subprocess.Popen for a command string, without a shell. UTF-8 in and out."""
    argv, discard_stderr = parse(cmd)
    if discard_stderr:
        kwargs["stderr"] = subprocess.DEVNULL
    if kwargs.pop("text", False):
        kwargs["encoding"] = "utf-8"
    if "encoding" in kwargs:
        kwargs.setdefault("errors", "replace")
    for key, value in plat.popen_flags(kwargs.pop("new_group", False)).items():
        kwargs[key] = kwargs.get(key, 0) | value
    return subprocess.Popen(_resolve(argv), **kwargs)


def output(cmd, input_text=None):
    """Combined stdout+stderr of a command (like utils.run_cmd), stripped. Problems that stop the
    command from starting are returned as text instead of raised."""
    try:
        process = popen(cmd, stdin=subprocess.PIPE if input_text is not None else None,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except UnsupportedCommand as exc:
        return str(exc)
    except OSError as exc:
        return f"{shlex.split(cmd)[0]}: {exc.strerror or exc}"
    stdout, _ = process.communicate(input=input_text)
    return (stdout or "").strip()
