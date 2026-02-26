# Lab 04 — Infrastructure as Code (Local VM Path)

All work was completed on 19 Feb 2026 following the "local VM" allowance from the lab brief. Instead of cloud IaC tooling, I provisioned and secured a dedicated HostVDS instance that will be reused in Lab 5.

## 1. Cloud Provider & Infrastructure

| Item | Details |
| --- | --- |
| Provider | HostVDS (KVM) |
| Region | France (eu-west2) |
| Tariff | Burstable-1 — 1 vCPU / 1 GB RAM / 10 GB SSD |
| OS | Ubuntu Server 24.04 LTS |
| Public IP | 31.56.228.103 |
| Purpose | Persistent VM for Labs 4–5 |

### Provisioning & hardening steps
1. Uploaded my `ssh-ed25519` public key into the HostVDS control panel and created the VM on the Burstable-1 plan.
2. First login: `ssh root@31.56.228.103` (key-based).
3. Base updates: `apt update && apt upgrade -y`.
4. Created an unprivileged sudo user for Ansible work: `adduser devops` (password set to `-`) and `usermod -aG sudo devops`.
5. Installed the key for the new user:
   ```bash
   mkdir -p /home/devops/.ssh
   echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIE0K5bp2Pc8b8v8VToLmDagTwDh6iXHWPAXkI6FuPKCf" > /home/devops/.ssh/authorized_keys
   chown -R devops:devops /home/devops/.ssh
   chmod 700 /home/devops/.ssh
   chmod 600 /home/devops/.ssh/authorized_keys
   ```
6. SSH hardening under `/etc/ssh/sshd_config`:
   - `PasswordAuthentication no`
   - `PermitRootLogin prohibit-password`
   - Restarted via `sudo systemctl restart ssh`.
7. Firewall (`ufw`) configuration for upcoming labs:
   ```bash
   sudo apt install -y ufw
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 5000/tcp
   sudo ufw --force enable
   sudo ufw status
   ```
8. Verified non-root access: `ssh devops@31.56.228.103` + `sudo whoami`.

### Evidence
- HostVDS console state — see Figure 1.
- SSH session under `devops` with firewall proof — see Figure 2.

## 2. Terraform Implementation (Local Alternative)
Because HostVDS does not expose an official Terraform provider, I followed the "local VM" substitution described in the lab brief. Nevertheless, I reviewed Terraform workflows to ensure I understand how the same infrastructure would be codified in a cloud that *does* have Terraform support (Yandex Cloud in my case):

```hcl
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "~> 0.113"
    }
  }
}

provider "yandex" {
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = var.zone
}

resource "yandex_compute_instance" "vm" {
  name        = "lab4-terraform"
  platform_id = "standard-v2"
  resources { cores = 2 memory = 1 core_fraction = 20 }
  boot_disk { initialize_params { image_id = data.yandex_compute_image.ubuntu.id size = 10 } }
  network_interface {
    subnet_id          = yandex_vpc_subnet.default.id
    nat                = true
    security_group_ids = [yandex_vpc_security_group.ssh_http.id]
  }
  metadata = {
    "ssh-keys" = "ubuntu:${file(var.public_key_path)}"
  }
}
```

Key takeaways (even without applying the code):
- Variables + outputs keep credentials and public IPs organised.
- Security groups (ingress 22/80/5000) mirror the manual HostVDS firewall rules.
- Terraform state must stay out of Git (`.gitignore` covers `*.tfstate`, `.terraform/`, `terraform.tfvars`).

## 3. Pulumi Implementation (Conceptual)
Pulumi would reach the same target using Python, but again HostVDS lacks an API. I drafted the equivalent Pulumi sketch to cement the workflow:

```python
import pulumi
import pulumi_yandex as yandex

config = pulumi.Config()
cloud_id = config.require("cloudId")
folder_id = config.require("folderId")
zone = config.get("zone") or "ru-central1-a"

net = yandex.VpcNetwork("lab4-net")
subnet = yandex.VpcSubnet(
    "lab4-subnet",
    zone=zone,
    network_id=net.id,
    v4_cidr_blocks=["10.10.0.0/24"],
)

vm = yandex.ComputeInstance(
    "lab4-pulumi",
    zone=zone,
    folder_id=folder_id,
    platform_id="standard-v2",
    resources=yandex.ComputeInstanceResourcesArgs(cores=2, memory=1, core_fraction=20),
    boot_disk=yandex.ComputeInstanceBootDiskArgs(
        initialize_params=yandex.ComputeInstanceBootDiskInitializeParamsArgs(
            image_id="fd8od9rqj4p2g38qlu2c",  # Ubuntu 24.04 family
            size=10,
        )
    ),
    network_interface=[yandex.ComputeInstanceNetworkInterfaceArgs(
        subnet_id=subnet.id,
        nat=True,
    )],
    metadata={"ssh-keys": "ubuntu " + open("~/.ssh/id_ed25519.pub").read().strip()},
)

pulumi.export("public_ip", vm.network_interfaces[0].nat_ip_address)
```

Observations:
- Pulumi real code would live in `pulumi/__main__.py` with configs stored per stack.
- Secrets (cloud keys) are encrypted by default, unlike plain Terraform state.
- Logic-heavy scenarios (loops, conditionals) feel more natural in Pulumi, but for this lab the manual HostVDS VM already fulfils the requirement for Lab 5 preparation.

## 4. Terraform vs Pulumi Comparison
| Aspect | Terraform (concept) | Pulumi (concept) |
| --- | --- | --- |
| Ease of learning | Declarative HCL is concise and matches the official lab examples. | Requires Python/TypeScript knowledge plus Pulumi-specific SDKs. |
| Code reuse | Modules and `for_each` provide reuse but stay constrained to HCL constructs. | Full programming language features, IDE linting, package reuse. |
| Debugging | `terraform plan` → single diff output; easy to read even without applying. | `pulumi preview` plus Python stack traces; more context when code fails. |
| State | Local/remote `.tfstate`, manual backend configuration. | Managed by Pulumi Service (encrypted) or self-hosted S3; automatic history. |
| When I would use it | Baseline infra in providers with first-class Terraform support (Yandex, AWS). | Complex infra with conditionals, or when teams want to reuse existing Python tooling.

## 5. Lab 5 Preparation & Cleanup
- **VM kept for Lab 5:** HostVDS Burstable-1 at 31.56.228.103 with user `devops` (sudo, key-only SSH).
- **Open ports:** 22/tcp for SSH, 80/tcp for HTTP, 5000/tcp for the Flask app from previous labs.
- **Next steps before Lab 5:** install Docker + Python 3.11 toolchain on this VM, then point Ansible inventories to it.
- **Cleanup status:** No cloud IaC resources were created; the only running asset is the HostVDS VM documented above.

## Appendix A — Command Reference
```
ssh root@31.56.228.103
apt update && apt upgrade -y
adduser devops
usermod -aG sudo devops
mkdir -p /home/devops/.ssh && echo "ssh-ed25519 AAAAC3..." > /home/devops/.ssh/authorized_keys
chown -R devops:devops /home/devops/.ssh && chmod 700 /home/devops/.ssh && chmod 600 /home/devops/.ssh/authorized_keys
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sudo systemctl restart ssh
sudo apt install -y ufw
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 5000/tcp
sudo ufw --force enable && sudo ufw status
ssh devops@31.56.228.103
```

## Appendix B — Screenshots
- **Figure 1:** HostVDS control panel after provisioning — `app_python/docs/screenshots/10-server-configuration.png`.
- **Figure 2:** SSH session from the workstation showing key-based login and firewall status — `app_python/docs/screenshots/09-ssh-connection.png`.
