{ pkgs ? import <nixpkgs> { } }:

let
  python = pkgs.python312;
  pyPkgs = pkgs.python312Packages;
  lib = pkgs.lib;
  pythonEnv = python.withPackages (ps: [
    ps.flask
    ps.gunicorn
    ps."python-json-logger"
    ps."prometheus-client"
  ]);
  pythonCheckEnv = python.withPackages (ps: [
    ps.flask
    ps.gunicorn
    ps."python-json-logger"
    ps."prometheus-client"
    ps.pytest
  ]);

  src = lib.cleanSourceWith {
    src = ./.;
    filter = path: type:
      let
        relPath = lib.removePrefix ((toString ./. ) + "/") (toString path);
      in
      !(
        relPath == "data/visits"
        || relPath == "result"
        || lib.hasPrefix "result-" relPath
        || lib.hasPrefix ".pytest_cache" relPath
        || lib.hasInfix "/.pytest_cache/" relPath
        || lib.hasPrefix "__pycache__" relPath
        || lib.hasInfix "/__pycache__/" relPath
      );
  };
in
pkgs.stdenvNoCC.mkDerivation rec {
  pname = "devops-info-service";
  version = "1.0.0";
  inherit src;

  nativeBuildInputs = [
    pkgs.makeWrapper
  ];

  doCheck = true;

  checkPhase = ''
    runHook preCheck
    export PYTHONPATH="$PWD"
    "${pythonCheckEnv}/bin/python" -m pytest tests -q
    runHook postCheck
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin" "$out/libexec/${pname}"
    cp app.py "$out/libexec/${pname}/app.py"
    cp -r data "$out/libexec/${pname}/data"

    makeWrapper "${pythonEnv}/bin/python" "$out/bin/devops-info-service" \
      --add-flags "$out/libexec/${pname}/app.py" \
      --set-default HOST 0.0.0.0 \
      --set-default PORT 5000 \
      --set-default VISITS_FILE /tmp/devops-info-service-visits

    runHook postInstall
  '';

  meta = {
    description = "DevOps course info service packaged reproducibly with Nix";
    mainProgram = "devops-info-service";
  };
}
