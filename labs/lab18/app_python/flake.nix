{
  description = "DevOps Info Service reproducible build with Nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {
      packages.${system} = {
        default = import ./default.nix { inherit pkgs; };
        dockerImage = import ./docker.nix { inherit pkgs; };
      };

      apps.${system}.default = {
        type = "app";
        program = "${self.packages.${system}.default}/bin/devops-info-service";
      };

      devShells.${system}.default = pkgs.mkShell {
        packages = with pkgs; [
          python312
          python312Packages.flask
          python312Packages.gunicorn
          python312Packages."python-json-logger"
          python312Packages."prometheus-client"
          python312Packages.pytest
        ];
      };
    };
}
