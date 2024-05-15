# backporter
A tool for backporting changes of C files.

## Description
This tool follows the standard procedure of backporting by invoking the `diff` and `patch` utilities but in addition to it the tool also supports logging of the processed and rejected hunks in JSON format. The detailed description of the algorithm follows:
1. A temporary directory is created
2. `diff` is launched with `begin` and `after` files and the output is written into `diff.patch` file in the temporary directory.
3. `patch` is launched to merge `diff.patch` into `target` configured to write potential conflicts into `reject` file in the temporary directory.
4. If `--log` option is provided, the files are parsed and combined to indicate the hunks that have been merged and the ones that have been rejected

## How to launch
The tool can be launched as a python file on Linux or as a docker container on any platform supporting docker runtime.

### Linux
To launch the tool on Linux:
1. Download the `backport.py` and `formats.py` and put them next to one another
2. Make sure that you have the `diff` and `patch` utilities installed. This can be checked by invoking the `which diff` and `which patch` commands. If the commands don't produce any output, you have to install them. On Ubuntu/Debian this can be done via `apt install` like following:
```
apt update
apt install rcs
apt install patch
```
3. Make sure that you have python3 installed
4. `cd` to the directory where you have stored the `backport.py` and `formats.py`.
5. Launch the `python3 ./backport.py <path-to-before> <path-to-after> <path-to-target> --log <path-to-json-log>`
6. Open the log file to examine the processed hunks

### Docker
To launch the docker image containing the most recent version of the tool:
1. Make sure that you have docker installed on your system
2. Run the following command: `docker run --rm -v <path-to-files>:/data ventice/backporter /data/<before> /data/<after> /data/<target> --log /data/history.json` where `<path-to-files>` is the path to the local directory where all the three files can be found and `<before>`, `<after>` and `<target>` are the paths relative to the `<path-to-files>`. Slashes in `<path-to-files>` are to be specified in platform-specific manner, and in `<before>`, `<after>` and `<target>` in the Linux way
3. The command will download the docker image, mount the specified directory as a volume into the container, run the command and delete the container leaving the patched file and the log on the host system.

## Tests
The unit tests are located in the `tests` directory. To launch them make sure you have `pytest` installed and simply invoke the `pytest` command in the project root directory.

## CI/CD
All the pushes to the `main` branch are automatically built into a docker image and pushed to the [ventice/backporter](https://hub.docker.com/repository/docker/ventice/backporter/general) image.