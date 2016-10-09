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
source=("$pkgname::git+http://github.com/asnt/${pkgname%-git}.git")
md5sums=(SKIP)

pkgver() {
    cd "$srcdir/${pkgname}"
    printf "r%s.%s" "$(git rev-list --count HEAD)" \
                    "$(git rev-parse --short HEAD)"
}

package() {
  cd "$srcdir/$pkgname"
  python setup.py install --root="$pkgdir"
}

