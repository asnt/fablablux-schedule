# Maintainer: asnt <snt.alex@gmail.com>
pkgname=python-fablab-schedule-git
pkgver=latest
pkgrel=1
pkgdesc='FabLab wall schedule scanner'
arch=('any')
license=('GPL')
depends=('python'
         'python-numpy'
         'python-requests'
         'opencv')
makedepends=('git')
provides=("${pkgname%-git}")
conflicts=("${pkgname%-git}")
source=("$pkgname::git+https://github.com/asnt/fablablux-schedule.git")
md5sums=('SKIP')

pkgver() {
    cd "$srcdir/${pkgname}"
    printf "r%s.%s" "$(git rev-list --count HEAD)" \
                    "$(git rev-parse --short HEAD)"
}

package() {
  cd "$srcdir/$pkgname"
  python setup.py install --root="$pkgdir"
  install -Dm644 "fablab-schedule.service" \
                 "$pkgdir/usr/lib/systemd/system/fablab-schedule.service"
}

