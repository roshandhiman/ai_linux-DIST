#!/usr/bin/env bash
# Install a curated set of cybersecurity tools for Kali/Debian-based systems.
# Usage: sudo ./scripts/install_cybersecurity_tools.sh
#
# This script intentionally does not add unofficial repositories. If a package is
# unavailable in the configured repositories, it is reported clearly and the script
# continues with the rest of the installation list.

set -u
IFS=$'\n\t'

PACKAGES=(
    "nmap"
    "metasploit-framework"
    "burpsuite"
    "wireshark"
    "sqlmap"
    "aircrack-ng"
    "hashcat"
    "john"
    "hydra"
    "netexec"
    "responder"
    "gobuster"
    "nikto"
    "ffuf"
    "autopsy"
    "theharvester"
    "recon-ng"
    "exploitdb"
    "tcpdump"
    "libimage-exiftool-perl"
    "airgeddon"
)

SUCCESSFUL=()
FAILED=()
UNAVAILABLE=()
TOTAL_PACKAGES=${#PACKAGES[@]}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf '%s\n' "$*" >&2
}

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        if command -v sudo >/dev/null 2>&1; then
            warn "This script requires root privileges. Requesting sudo..."
            exec sudo -E env "DEBIAN_FRONTEND=noninteractive" bash "$0" "$@"
        else
            warn "This script must be run as root or with sudo."
            exit 1
        fi
    fi
}

detect_distribution() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        DISTRO_NAME="${PRETTY_NAME:-${NAME:-Unknown}}"

        case "${ID:-}" in
            kali|debian|ubuntu|linuxmint|pop|raspbian)
                return 0
                ;;
        esac

        case "${ID_LIKE:-}" in
            *debian*|*ubuntu*|*kali*)
                return 0
                ;;
        esac
    fi

    warn "Unsupported or unknown Linux distribution: ${DISTRO_NAME:-unknown}. This script supports Debian/Kali/Ubuntu-based systems only."
    exit 1
}

check_apt() {
    if ! command -v apt-get >/dev/null 2>&1; then
        warn "APT is not available on this system. This script supports Debian/Kali/Ubuntu-based systems using apt-get only."
        exit 1
    fi
}

package_available() {
    local pkg="$1"
    if apt-cache policy "$pkg" 2>/dev/null | grep -Eq 'Candidate:|Installed:'; then
        return 0
    fi
    return 1
}

update_repositories() {
    log "Updating package repositories..."
    if ! apt-get update; then
        warn "Failed to update repositories. Aborting before installation."
        exit 1
    fi
}

install_one_package() {
    local pkg="$1"
    local index="$2"
    local total="$3"

    printf '\n[%s/%s] Installing: %s\n' "$index" "$total" "$pkg"

    if ! package_available "$pkg"; then
        warn "Package '$pkg' is unavailable in the configured repositories."
        UNAVAILABLE+=("$pkg")
        return
    fi

    if apt-get install -y -- "$pkg"; then
        if dpkg -s "$pkg" >/dev/null 2>&1; then
            log "Verified: '$pkg' installed successfully."
            SUCCESSFUL+=("$pkg")
        else
            warn "Installation of '$pkg' appeared to succeed, but verification failed."
            FAILED+=("$pkg")
        fi
    else
        warn "Installation failed for '$pkg'. Continuing with remaining packages."
        FAILED+=("$pkg")
    fi
}

print_final_report() {
    log ""
    log "========================================="
    log "Cybersecurity tools installation summary"
    log "========================================="

    if ((${#SUCCESSFUL[@]} > 0)); then
        log "Successfully installed:"
        printf '  - %s\n' "${SUCCESSFUL[@]}"
    else
        log "Successfully installed: none"
    fi

    if ((${#FAILED[@]} > 0)); then
        log "Failed or not installed:"
        printf '  - %s\n' "${FAILED[@]}"
    else
        log "Failed or not installed: none"
    fi

    if ((${#UNAVAILABLE[@]} > 0)); then
        log "Unavailable in configured repositories:"
        printf '  - %s\n' "${UNAVAILABLE[@]}"
    else
        log "Unavailable in configured repositories: none"
    fi

    log ""
    log "Total packages processed: $TOTAL_PACKAGES"
    log "Completed with ${#SUCCESSFUL[@]} successful installs, ${#FAILED[@]} failed installs, and ${#UNAVAILABLE[@]} unavailable packages."
}

main() {
    require_root "$@"
    detect_distribution
    check_apt

    export DEBIAN_FRONTEND=noninteractive

    log "Detected Linux distribution: ${DISTRO_NAME:-$(. /etc/os-release >/dev/null 2>&1 && printf '%s' "${PRETTY_NAME:-${NAME:-Unknown}}" || printf '%s' 'Unknown')}"
    log "This script will install ${TOTAL_PACKAGES} cybersecurity packages one by one."
    log "Packages unavailable in the configured repositories will be reported clearly."

    update_repositories

    local i=1
    for pkg in "${PACKAGES[@]}"; do
        install_one_package "$pkg" "$i" "$TOTAL_PACKAGES"
        i=$((i + 1))
    done

    print_final_report

    if ((${#FAILED[@]} > 0 || ${#UNAVAILABLE[@]} > 0)); then
        log "Note: Some packages were not installed successfully. Review the report above."
        exit 1
    fi

    log "All requested packages were installed successfully."
    exit 0
}

main "$@"
