# Running Open Toontown on NixOS

This guide describes the working NixOS development setup for Open Toontown.
It builds the project's custom Panda3D fork and the matching Astron server
from source. The ordinary Panda3D package does not include the required OTP
and Toontown extensions.

The instructions currently target `x86_64-linux`.

## Repository layout

Place the related repositories next to each other as follows:

```text
code/
├── open-toontown/
│   └── resources/
├── panda3d/
└── astron-source/
```

The following revisions are known to work together:

| Component | Revision |
| --- | --- |
| Panda3D fork | `06615744481946654610833679a0893589114504` |
| Astron | `3ad54903b6ec3d4fd796043f558732fbb326a59c` |
| Resources | `d8c73a9978633979ddf2ef8813f0152037a0d978` |

The Astron revision is the revision embedded in the Windows binary supplied
with this version of Open Toontown.

## Clone the resources

From the Open Toontown repository root:

```sh
git clone https://github.com/open-toontown/resources.git resources
git -C resources checkout d8c73a9978633979ddf2ef8813f0152037a0d978
```

The game expects paths such as `resources/phase_3` relative to its repository
root. The `resources` directory is intentionally ignored by Git.

## Enter the development environment

The Nix flake pins Python 3.9 and supplies the native build and runtime
libraries needed by Panda3D and Astron:

```sh
nix develop
```

If `flake.nix` is still untracked in a local checkout, use:

```sh
nix develop path:.
```

Running `git add flake.nix flake.lock` also makes the normal command work;
staging files does not commit or push them.

Enter `nix develop` before activating `.venv`. Repeat this order in every new
terminal used to run a server or client:

```sh
cd /path/to/open-toontown
nix develop
source .venv/bin/activate
```

The Nix shell provides native shared libraries, while `.venv` provides the
custom Panda3D Python package.

## Build Panda3D

Clone and select the tested custom fork revision:

```sh
git clone https://github.com/open-toontown/panda3d.git ../panda3d
git -C ../panda3d checkout 06615744481946654610833679a0893589114504
```

From the Open Toontown root, inside `nix develop`, run:

```sh
./nix/build-panda3d.sh
```

The helper performs the following operations:

- Creates `.venv` and installs `requirements.txt` when necessary.
- Copies the Panda3D checkout to the ignored `local/` directory.
- Applies the Nix ZIP-timestamp compatibility patch.
- Builds a Python 3.9 wheel with the OTP and Toontown extensions.
- Installs the wheel into `.venv` and verifies the important imports.

The first build can take several minutes. Missing optional integrations such
as NVIDIA Cg, ARToolkit, VRPN, FFmpeg, or MongoDB are not required for this
game.

To use a source checkout in another location or change the parallelism:

```sh
PANDA3D_SOURCE=/path/to/panda3d PANDA3D_BUILD_THREADS=16 \
  ./nix/build-panda3d.sh
```

To force a fresh build, remove the generated build directories and rerun the
helper:

```sh
rm -rf local/panda3d-build local/panda3d-wheel-source
./nix/build-panda3d.sh
```

Verify the installed extensions with:

```sh
.venv/bin/python -c \
  'import panda3d.core, panda3d.otp, panda3d.toontown; print(panda3d.core.PandaSystem.get_version_string())'
```

## Build Astron

Clone and select the revision matching the bundled Windows server:

```sh
git clone https://github.com/Astron/Astron.git ../astron-source
git -C ../astron-source checkout 3ad54903b6ec3d4fd796043f558732fbb326a59c
```

This 2021 revision treats every compiler warning as an error. GCC 13 detects
an uninitialized fallback in `src/core/Logger.cpp`. In `Logger::log`, add a
default case to the severity switch after `LSEVERITY_FATAL`:

```cpp
    case LSEVERITY_FATAL:
        sevtext = "FATAL";
        break;
    default:
        sevtext = "UNKNOWN";
        break;
```

Enter the Open Toontown Nix shell, then configure Astron from its own source
directory:

```sh
cd /path/to/open-toontown
nix develop
cd ../astron-source

cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_TESTS=OFF \
  -DBUILD_DB_MONGO=OFF \
  -DBUILD_DB_POSTGRESQL=OFF \
  -DBUILD_DB_MYSQL=OFF \
  -DBUILD_DB_SQLITE=OFF \
  -DBUILD_DB_YAML=ON \
  -DBUILD_DBSERVER=ON \
  -DBUILD_STATESERVER=ON \
  -DBUILD_STATESERVER_DBSS=ON \
  -DBUILD_EVENTLOGGER=ON \
  -DBUILD_CLIENTAGENT=ON \
  -DYAMLCPP_USE_STATIC_LIBS=OFF \
  -DYAMLCPP_INCLUDE_DIR="$ASTRON_YAML_INCLUDE" \
  -DYAMLCPP_LIBRARY_RELEASE="$ASTRON_YAML_LIBRARY" \
  -DLIBUV_INCLUDE_DIR="$ASTRON_LIBUV_INCLUDE" \
  -DLIBUV_LIBRARY="$ASTRON_LIBUV_LIBRARY"

cmake --build build --parallel 8
./build/astrond --version
```

The version output should contain:

```text
Revision: 3ad54903
Components: State Server (With DBSS capablities), Event Logger, Client Agent, Database (With YAML Support)
```

Copy the resulting binary to the location expected by the Linux launcher:

```sh
cd /path/to/open-toontown
mkdir -p astron/linux
cp ../astron-source/build/astrond astron/linux/astrond
chmod +x astron/linux/astrond
```

The binary is dynamically linked to Nix store libraries, so run it from the
same pinned `nix develop` environment.

## Start the server and clients

Use four terminals and start the components in this order:

```text
Astron → UberDOG → AI server → client
```

In every terminal, prepare the environment first:

```sh
cd /path/to/open-toontown
nix develop
source .venv/bin/activate
cd linux
```

Run one command per terminal, waiting for each component to finish starting
before launching the next:

```sh
./start-astron-server.sh
```

```sh
./start-uberdog-server.sh
```

```sh
./start-ai-server.sh
```

```sh
./start-game.sh
```

Additional clients can be started in additional prepared terminals. The game
launcher sets `LOGIN_TOKEN=dev` for local development.

The default local ports are:

| Port | Service |
| --- | --- |
| `7197` | Event logger |
| `7198` | Game client connections |
| `7199` | Message director |

The Linux launch scripts currently assume that they are invoked from the
`linux/` directory because they use relative paths.

## Generated and external files

The following required files are deliberately not stored in this repository:

- `resources/`: cloned game assets.
- `.venv/`: Python environment containing the custom Panda3D wheel.
- `local/`: Panda3D source copy and build output.
- `../panda3d/`: custom Panda3D source checkout.
- `../astron-source/`: matching Astron source checkout and GCC fix.
- `astron/linux/astrond`: locally built Astron executable unless explicitly
  added to a personal fork.

Keep the flake lock file committed in a personal fork to retain the tested
Nixpkgs dependency versions.
