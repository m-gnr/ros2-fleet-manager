# Tek robotlu simulation doğrulaması: Aşama B2

Tarih: 23 Ekim 2026 (Europe/Istanbul).

## Durum ve kapsam

Devamı: [simulation-stage-b2-continuation-2026-10-23.md](simulation-stage-b2-continuation-2026-10-23.md), B2 GEÇTİ (2/3 koşu, 2 temiz başarı)

**DURULDU: Paket kurulumu sırasında yeni hata çıktısı görüldü. B2 hazırlık ve canlı doğrulama adımları başlatılmadı. Canlı koşu: 0/3.**

Resmi Humble Nav2 paketleri linux/arm64 image'a kuruldu; build çıkışı 0, kurulu paket durumları `installed`, `dpkg --audit` çıktısı boş. Buna rağmen aşağıdaki paket betiği hatası nedeniyle kullanıcının “her adımda yeni bir hata çıkarsa dur” sınırı uygulandı. Bu sonuç Nav2 çalışması veya B2 başarısı değildir.

Bu kayıt [B1 kaydından](simulation-stage-b-2026-10-23.md) ayrıdır. B1 dosyaları korunur. Docker yerleşimi onaylanmış sayılmaz. [Proje bağlamındaki](project-context.md) kaynak önceliği geçerlidir. Backend test istemcisi henüz eklenmedi; uygulama komut sahipliği değişmez.

## Kurulum planı ve kanıt

Taban, B1'in başarılı yerel `ros2-fleet-simulation-lidar-check:humble-fortress` image'ıdır. Önce geçici linux/arm64 container içinde `apt-get update -o APT::Update::Error-Mode=any`, resmi depo adayları ve APT kurulum simülasyonu denetlendi (0). Resmi `packages.ros.org/ros2/ubuntu`, `jammy/main arm64` adayları [ayrı Dockerfile](../docker/simulation-nav2-check/Dockerfile) içinde sabitlendi. Ardından tek build ile `--no-install-recommends` kurulumu yapıldı (0).

APT planı ve gerçek kurulum: 472 yeni paket, 2 yükseltme, 0 kaldırma; 7 paket yükseltilmeden kaldı. Arşiv indirmesi 230 MB, 8 dakika 40 saniye; APT build katmanı 636.9 saniye sürdü. Nav2 metapaketinin bağımlılıkları RViz ve SLAM paketlerini de içerdi; GUI veya SLAM çalıştırılmadı. Paket isimleri [resmi Nav2 paket kaydı](https://index.ros.org/p/nav2_bringup/) ile karşılaştırıldı. Gerçek kurulum kanıtı komut ekindeki APT ve dpkg çıktılarıdır.

| Paket | Kurulu sürüm | Mimari / durum |
| --- | --- | --- |
| ros-humble-navigation2 | 1.1.20-1jammy.20260916.170645 | arm64 / installed |
| ros-humble-nav2-bringup | 1.1.20-1jammy.20260916.171610 | arm64 / installed |
| ros-humble-nav2-amcl | 1.1.20-1jammy.20260916.053520 | arm64 / installed |
| ros-humble-nav2-map-server | 1.1.20-1jammy.20260916.053559 | arm64 / installed |
| ros-humble-nav2-controller | 1.1.20-1jammy.20260916.131334 | arm64 / installed |
| ros-humble-nav2-planner | 1.1.20-1jammy.20260916.131155 | arm64 / installed |
| ros-humble-nav2-bt-navigator | 1.1.20-1jammy.20260916.130559 | arm64 / installed |
| ros-humble-nav2-lifecycle-manager | 1.1.20-1jammy.20260916.123216 | arm64 / installed |

Image: `ros2-fleet-simulation-nav2-check:humble-fortress`, platform **linux/arm64**, Ubuntu 22.04.5 LTS. Image ID: `sha256:dc766635005bba89c4f7b2ea9fcaf6b5273f4421a6a03116db819f49e05f21c0`. Taban B1 ID'si build çıktısında `sha256:ba741517e3ef0d109d05315983a6ded3e16e79693d49a4f968e65f2b73695162` olarak doğrulandı.

Image yalnız bağımlılık hazırlığıdır. Kendi B2 giriş betiği veya Compose override'ı henüz yoktur; tabanın B1 CMD'sini devralır. Bu image'ı komutsuz çalıştırmak B2 testi değildir. Paket sorguları açık komutla ve `--rm` ile çalıştırıldı.

## Yeni hata ve durma noktası

Build'in `systemd` kurulum bölümünde şu çıktı görüldü:

```text
#5 618.4 Setting up systemd (249.11-0ubuntu3.23) ...
#5 618.4 Created symlink /etc/systemd/system/getty.target.wants/getty@tty1.service → /lib/systemd/system/getty@.service.
#5 618.4 Created symlink /etc/systemd/system/multi-user.target.wants/remote-fs.target → /lib/systemd/system/remote-fs.target.
#5 618.4 Created symlink /etc/systemd/system/dbus-org.freedesktop.resolve1.service → /lib/systemd/system/systemd-resolved.service.
#5 618.4 Created symlink /etc/systemd/system/multi-user.target.wants/systemd-resolved.service → /lib/systemd/system/systemd-resolved.service.
#5 618.4 ln: failed to create symbolic link '/etc/resolv.conf': Device or resource busy
#5 618.4 Created symlink /etc/systemd/system/sysinit.target.wants/systemd-pstore.service → /lib/systemd/system/systemd-pstore.service.
#5 618.4 Initializing machine ID from random generator.
```

Bağları oluşturan resmi paket betiğidir; elle symlink veya dosya kopyalama yapılmadı. APT bu hata satırından sonra devam etti ve build 0 ile bitti. Hata satırı bastırılmadı, giderilmeye çalışılmadı ve yeniden build yapılmadı. Çalışmaya etkisi **doğrulanmadı**; hata zararsız varsayılıp sonraki adıma geçilmedi. Build sürerken salt okunur `docker buildx history ls` ve `docker buildx history logs p007iljt9ilrjuqdlo8341bjr` ile ilerleme izlendi (0). Sonraki işlemler yalnız sonuç/sürüm kaydı ve temizlik doğrulamasıdır.

Kurulum çıktısındaki `debconf`, `invoke-rc.d` ve eksik man sayfası bağlarına ilişkin `update-alternatives` uyarıları da komut ekinde korunur. Tek paket kurulumu denemesi vardır; başarısız canlı Nav2 koşusu yoktur.

İlk sonuç sorgusunda `dpkg-query` biçimi yanlışlıkla iç shell tarafından genişletildi ve sekiz boş satır döndü (0). Bu çıktı sürüm kanıtı sayılmadı. Aynı salt okunur sorgu doğrudan `dpkg-query` argümanı olarak yapıldı; yukarıdaki `installed` durumları alındı (0). İki komut da ekte korunur.

## Komutlar ve çıktılar

[Komut eki](simulation-stage-b2-commands-2026-10-23.md), komutları, çıkış kodlarını ve gerçek çıktıları içerir. Uzun rutin paket indirme/açma/kurma listeleri açık işaretle kısaltıldı; hata ve uyarı satırları, ilgili bağlam, sürümler, APT özeti ve image digest'leri korundu. Başlangıç `git status --short` çıktısı boştu (0). Bağlam, v2.3 geçiş kaydı, B1 kaydı/komut eki ve mevcut deney betikleri okundu.

## Doğrulanmadı ve sınırlar

- `/etc/resolv.conf` paket betiği hatasının çalışma zamanına etkisi: Kullanıcı talimatı gereği bu hata "bilinen Docker build davranışı, izinli" olarak işaretlendi. `systemd` paketinin `ii` (tam kurulu) olduğu ve `nav2_bringup` paketinin `/opt/ros/humble` altında erişilebilir olduğu salt okunur komutlarla kanıtlandı. Ardından yapılan iki temiz canlı koşuda (`01` ve `02`) Nav2 bringup, lifecycle ve `NavigateToPose` başarıyla tamamlandığı için çalışma zamanına olumsuz etkisi olmadığı **doğrulandı** (ayrıntılar [B2 devam kaydında](simulation-stage-b2-continuation-2026-10-23.md)).
- B2 haritası (pgm/yaml), dünya tutarlılığı ve config şemaları; oluşturulmadı (sonradan tamamlandı, bkz. devam kaydı).
- B2 için null olmayan harita yolu ve Nav2 parametre config'i; oluşturulmadı (sonradan tamamlandı, bkz. devam kaydı).
- Nav2 için lidar ışın sayısı/hızı, gerçek scan hızı ve container CPU kullanımı; ölçülmedi (sonradan tamamlandı, bkz. devam kaydı).
- Nav2 bringup, use_sim_time, lifecycle ve map→odom→base_link zinciri; başlatılmadı (sonradan tamamlandı, bkz. devam kaydı).
- Config kaynaklı başlangıç pozu, AMCL yakınsaması ve poz hata eşikleri; denenmedi (sonradan tamamlandı, bkz. devam kaydı).
- Backend istemcisinden NavigateToPose goal/result ve odometri/AMCL ile hedefe varış; denenmedi (sonradan tamamlandı, bkz. devam kaydı).
- İki temiz başarılı B2 koşusu ve arada container/ağ kaldırma; canlı koşu başlamadığı için yapılmadı (sonradan tamamlandı, bkz. devam kaydı). Üst sınır üç canlı koşudur.

Çoklu robot, fleet.yaml, ExecuteTask, robot yürütücüsü, batarya, Fleet Manager, FastAPI ve frontend eklenmedi. Docker onayı, mimari değişiklik veya yeni ürün politikası yoktur. v2.3 geçiş kaydı, Docker karar taslağı, PDF'ler ve kişisel notlar değişmedi.

## Dosyalar ve sonuç

Yalnız üç yeni dosya eklendi: bu kayıt, komut eki ve ayrı bağımlılık Dockerfile'ı. Önceki dosyalar değiştirilmedi. B2 Compose/config/kod eklenmeden duruldu. Yerel B2 bağımlılık image'ı inceleme için bırakıldı. Son dosya ve geçici container denetimleri komut ekindedir.
