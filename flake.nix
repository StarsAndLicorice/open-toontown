{
  description = "Open Toontown development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python39;
    in {
      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python
          python.pkgs.pip
          python.pkgs.setuptools
          python.pkgs.wheel
          gcc
          pkg-config
          bison
          flex

          libpng
          libjpeg
          libtiff
          zlib
          openssl
          freetype
          harfbuzz
          libvorbis
          opusfile
          openal
          xorg.libX11
          xorg.libXrandr
          xorg.libXcursor
          xorg.libXi
          xorg.libXxf86vm
          libGL
          mesa
          gtk3
          eigen
          bullet
          ode
          assimp
          openexr
          cmake
          boost
          yaml-cpp
          libuv
        ];

        # Native extensions installed in .venv can find their Nix-provided
        # runtime libraries when launched from `nix develop`.
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
          libpng libjpeg libtiff zlib openssl freetype harfbuzz
          libvorbis opusfile openal xorg.libX11 xorg.libXrandr
          xorg.libXcursor xorg.libXi xorg.libXxf86vm libGL mesa gtk3
          bullet ode assimp openexr stdenv.cc.cc.lib
        ]);

        CMAKE_PREFIX_PATH = pkgs.lib.makeSearchPath "lib/cmake" [
          pkgs.boost
          pkgs.yaml-cpp
          pkgs.libuv
        ];

        ASTRON_YAML_INCLUDE = "${pkgs.lib.getDev pkgs.yaml-cpp}/include";
        ASTRON_YAML_LIBRARY = "${pkgs.yaml-cpp}/lib/libyaml-cpp.so";
        ASTRON_LIBUV_INCLUDE = "${pkgs.lib.getDev pkgs.libuv}/include";
        ASTRON_LIBUV_LIBRARY = "${pkgs.libuv}/lib/libuv.so";

        # makepanda's generic filesystem search does not discover libraries
        # under /nix/store without explicit search roots.
        PANDA_PYTHON_INCDIR = "${python}/include";
        PANDA_PYTHON_LIBDIR = "${python}/lib";

        shellHook = ''
          echo "Open Toontown shell: Python ${python.version}"
          echo "Create/activate the environment with: source .venv/bin/activate"
        '';
      };
    };
}
