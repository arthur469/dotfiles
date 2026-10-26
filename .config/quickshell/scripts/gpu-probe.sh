#!/bin/sh

u=-; t=-
isnum() { case "$1" in ''|*[!0-9.]*) return 1;; *) return 0;; esac; }

# 1. NVIDIA
if command -v nvidia-smi >/dev/null 2>&1; then
  o=$(nvidia-smi --query-gpu=utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -n1)
  if [ -n "$o" ]; then
    a=$(echo "$o" | cut -d, -f1 | tr -d ' ')
    b=$(echo "$o" | cut -d, -f2 | tr -d ' ')
    isnum "$a" && u="$a"
    isnum "$b" && t="$b"
  fi
fi

# 2. AMD (amdgpu sysfs)
if [ "$u" = "-" ]; then
  best=""; bestmem=-1
  for d in /sys/class/drm/card[0-9]*/device; do
    [ -r "$d/gpu_busy_percent" ] || continue
    m=$(cat "$d/mem_info_vram_total" 2>/dev/null || echo 0)
    isnum "$m" || m=0
    if [ "$m" -gt "$bestmem" ]; then best="$d"; bestmem="$m"; fi
  done
  if [ -n "$best" ]; then
    a=$(cat "$best/gpu_busy_percent" 2>/dev/null)
    isnum "$a" && u="$a"
    if [ "$t" = "-" ]; then
      for h in "$best"/hwmon/hwmon*/temp1_input; do
        if [ -r "$h" ]; then t=$(( $(cat "$h") / 1000 )); break; fi
      done
    fi
  fi
fi

# 3. Intel via intel_gpu_top (needs CAP_PERFMON / root; silently skipped otherwise)
if [ "$u" = "-" ] && command -v intel_gpu_top >/dev/null 2>&1; then
  v=$(timeout 3 intel_gpu_top -J -s 500 -n 2 2>/dev/null | grep -o '"busy": *[0-9.]*' | grep -o '[0-9.]*$' | sort -n | tail -n1)
  isnum "$v" && u="$v"
fi

# 4. Unprivileged fallback: GPU clock as a load estimate (i915 / xe)
if [ "$u" = "-" ]; then
  for c in /sys/class/drm/card[0-9]*; do
    [ -d "$c" ] || continue
    for pair in \
      "$c/gt/gt0/rps_act_freq_mhz:$c/gt/gt0/rps_max_freq_mhz" \
      "$c/gt/gt0/rps_cur_freq_mhz:$c/gt/gt0/rps_max_freq_mhz" \
      "$c/gt_act_freq_mhz:$c/gt_max_freq_mhz" \
      "$c/gt_cur_freq_mhz:$c/gt_max_freq_mhz" \
      "$c/device/tile0/gt0/freq0/act_freq:$c/device/tile0/gt0/freq0/max_freq"; do
      f1=${pair%%:*}; f2=${pair#*:}
      [ -r "$f1" ] && [ -r "$f2" ] || continue
      cur=$(cat "$f1" 2>/dev/null); max=$(cat "$f2" 2>/dev/null)
      if isnum "$cur" && isnum "$max" && [ "$max" -gt 0 ]; then
        u=$(( cur * 100 / max )); [ "$u" -gt 100 ] && u=100
        break 2
      fi
    done
  done
fi

# Temperature fallback: any DRM card hwmon (i915 / xe / nouveau / amdgpu)
if [ "$t" = "-" ]; then
  for h in /sys/class/drm/card[0-9]*/device/hwmon/hwmon*/temp1_input; do
    if [ -r "$h" ]; then
      r=$(cat "$h" 2>/dev/null)
      if isnum "$r"; then t=$(( r / 1000 )); break; fi
    fi
  done
fi

echo "$u $t"
