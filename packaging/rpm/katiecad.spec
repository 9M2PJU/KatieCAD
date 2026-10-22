Name:           katiecad
Version:        0.2.2
Release:        1%{?dist}
Summary:        Lightweight CAD drawing tool (Python/Tkinter)
License:        MIT
URL:            https://github.com/Merecete/KatieCAD
# Built from a local checkout; see packaging/build-rpm.sh which injects
# %%{_sourcedir} contents. Upstream tarball URL for reference:
# Source0:      https://github.com/Merecete/KatieCAD/archive/refs/tags/v%{version}.tar.gz
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-tkinter
Requires:       python3-pillow
Requires:       python3-ezdxf
Recommends:     python3-pip
# Optional DWG helpers (not in Fedora repos, install via pip / external repo)
# Suggests:     (python3-ezdwg)

%description
KatieCAD is a lightweight 2D CAD drawing tool built with Python and
Tkinter, featuring drawing, editing and dimensioning tools, layers,
layout view with viewports, and DXF import/export via ezdxf plus
DWG import support.

%prep
%autosetup -n %{name}-%{version}

%build
# Nothing to compile (pure Python). Byte-compile for a sanity check.
python3 -m compileall -q KatieCAD.py katiecad_*.py

%install
rm -rf %{buildroot}
install -d %{buildroot}%{_datadir}/katiecad
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_datadir}/applications
install -d %{buildroot}%{_datadir}/pixmaps
install -d %{buildroot}%{_datadir}/icons/hicolor/512x512/apps
install -d %{buildroot}%{_datadir}/metainfo
install -d %{buildroot}%{_docdir}/%{name}

install -m 644 KatieCAD.py katiecad_*.py requirements.txt README.md %{buildroot}%{_datadir}/katiecad/
install -m 755 packaging/katiecad %{buildroot}%{_bindir}/katiecad
install -m 644 packaging/katiecad.desktop %{buildroot}%{_datadir}/applications/katiecad.desktop
install -m 644 KatieCAD.png %{buildroot}%{_datadir}/pixmaps/katiecad.png
install -m 644 KatieCAD.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/katiecad.png
install -m 644 packaging/katiecad.appdata.xml %{buildroot}%{_datadir}/metainfo/katiecad.appdata.xml

%files
%{_bindir}/katiecad
%{_datadir}/katiecad/
%{_datadir}/applications/katiecad.desktop
%{_datadir}/pixmaps/katiecad.png
%{_datadir}/icons/hicolor/512x512/apps/katiecad.png
%{_datadir}/metainfo/katiecad.appdata.xml
%license LICENSE
%doc README.md

%changelog
* Thu Oct 22 2026 KatieCAD Contributors - 0.2.2-1
- Initial RPM packaging.
