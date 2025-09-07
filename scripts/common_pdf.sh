#!/usr/bin/env bash
# ==============================================================================
# File: scripts/common_pdf.sh
# Purpose: Shared helpers for PDF passes (logging hooks, CSV writers, reliability)
#
# Used by: pass_pdf.sh (orchestrator), pass_pdf_txt.sh, pass_pdf_ocr_a.sh, pass_pdf_ocr_b.sh
#
# Key functions:
#   - clean_text: normalize page text for safe CSV embedding
#   - summarize_counts: derive pages/good/total_chars/coverage from counts.tsv
#   - write_outputs: emit 5-col CSV (or per-page CSV + pointer for huge docs)
#   - doc_reliability: compute median page reliability + %pages≥0.5 (0..1)
#   - page_reliability: score a single page's text (density + stopwords + repetition [+ OCR conf proxy])
#
# Env knobs (can be overridden via ENV):
#   PAGE_GOOD_MIN_CHARS=100     # legacy metric used for "good" in summaries only
#   HUGE_PAGES_THRESHOLD=500
#   HUGE_SIZE_BYTES=50000000
#   HUGE_TOTAL_CHARS=2000000
#   RELIABILITY_D_NORM=400      # chars that map to density=1.0
#
# Logging is expected to be provided by common.sh (log_info/log_warn/log_error).
# ==============================================================================

set -Eeuo pipefail

# shellcheck disable=SC1091
. /app/scripts/common.sh

# ---- thresholds (legacy + huge-doc behavior) ---------------------------------
: "${PAGE_GOOD_MIN_CHARS:=100}"
: "${HUGE_PAGES_THRESHOLD:=500}"
: "${HUGE_SIZE_BYTES:=50000000}"
: "${HUGE_TOTAL_CHARS:=2000000}"
: "${RELIABILITY_D_NORM:=400}"

clean_text() { sed 's/\r//g' | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/"/""/g'; }

count_chars() { printf '%s' "$1" | tr -d '\n\r\t ' | wc -c | awk '{print $1}'; }

pct() { awk -v g="$1" -v t="$2" 'BEGIN{ if (t<=0) print 0; else printf("%.1f",(100.0*g)/t) }'; }

summarize_counts() {
  # Arg: counts.tsv  (tab: page \t nonspace_chars)
  local counts="$1"
  local pages_total=0 good_pages=0 total_chars=0
  while IFS=$'\t' read -r p c; do
    [[ -z "${p:-}" || -z "${c:-}" ]] && continue
    ((pages_total++))
    (( c >= PAGE_GOOD_MIN_CHARS )) && ((good_pages++))
    (( total_chars += c ))
  done < "$counts"
  local coverage; coverage="$(pct "$good_pages" "$pages_total")"
  echo "$pages_total $good_pages $total_chars $coverage"
}

should_paginate() { # (pages_total size_bytes total_chars)
  local p="$1" s="$2" t="$3"
  if (( p >= HUGE_PAGES_THRESHOLD )) || (( s >= HUGE_SIZE_BYTES )) || (( t >= HUGE_TOTAL_CHARS )); then
    return 0; else return 1; fi
}

# --- quick sampler: decides if a PDF is likely scan-only (no useful text layer)
# Return: 0 (true) if looks scan-only; 1 otherwise
sample_text_layer() { # (pdf_path pages_total)
  local pdf="$1" pages="${2:-0}"
  # pick first, middle, last
  local p1=1 pm=$(( (pages>0) ? ((pages+1)/2) : 1 )) pl="$pages"
  (( pl<=0 )) && pl=1
  local sum=0 n p
  for p in "$p1" "$pm" "$pl"; do
    n="$(pdftotext -layout -f "$p" -l "$p" "$pdf" - 2>/dev/null | tr -d '\r\t ' | wc -c | awk '{print $1}')"
    [[ -z "$n" ]] && n=0
    sum=$(( sum + n ))
  done
  # threshold: if the three sampled pages together have < 90 non-space chars,
  # we treat it as scan-only. Adjust later if needed.
  if (( sum < 90 )); then
    return 0  # scan-only
  else
    return 1  # has text
  fi
}

# ---- reliability scoring ------------------------------------------------------
# small, embedded stopword list (lowercase)
_stopwords='a an and are as at be but by for from has have if in into is it its
  of on or that the their there these they this to was were what when where which
  who will with without within would about above after again against all also any
  because been before being below between both did do does doing down during each
  few further he her here hers herself him himself his how i into itself just me
  more most my myself no nor not now off once only other our ours ourselves out
  over own same she should so some such than then there’s they’re those through
  too under until up very we were what’s when’s where’s who’s why will you your
  yours yourself yourselves'

# Scores a single page's text (0..1). Arg1: text, Arg2: method ("txt"|"ocr")
page_reliability() {
  awk -v D_NORM="${RELIABILITY_D_NORM}" -v METHOD="${2:-txt}" -v STOPWORDS="$_stopwords" '
    function clamp(x,a,b){ return x<a?a:(x>b?b:x) }
    function tolower_str(s){ gsub(/[A-Z]/, "", s); return tolower(s) } # mawk compat
    BEGIN{
      # build stopword set
      split(STOPWORDS, arr, /[[:space:]]+/)
      for(i in arr){ if(arr[i]!=""){ sw[arr[i]]=1 } }
    }
    {
      text = $0
      # remove CRs
      gsub(/\r/, "", text)

      # density (D): non-whitespace chars normalized by D_NORM
      nonws = text; gsub(/[[:space:]]/, "", nonws)
      n = length(nonws)
      D = (D_NORM>0) ? (n / D_NORM) : 0
      if (D > 1) D = 1.0

      # wordiness / stopwords ratio (W)
      lower = tolower(text)
      gsub(/[^a-z]+/, " ", lower)
      gsub(/^ +| +$/, "", lower)
      num_tokens = split(lower, toks, / +/)
      sw_hits = 0
      if (num_tokens > 0) {
        for(i=1;i<=num_tokens;i++){ if(toks[i] in sw) sw_hits++ }
        W = clamp(sw_hits / num_tokens, 0, 1)
      } else {
        W = 0
      }

      # repetition penalty (R) = 1 - max_char_frequency_ratio
      # count on nonws, to avoid whitespace dominating
      split(nonws, chars, "")
      delete freq
      maxf = 0
      for(i=1;i<=length(nonws);i++){
        c = chars[i]; freq[c]++
        if (freq[c]>maxf) maxf=freq[c]
      }
      R = (length(nonws)>0) ? (1 - (maxf/length(nonws))) : 0

      # OCR confidence proxy (C)
      if (METHOD=="txt") C = 1.0;
      else C = D;  # rough proxy without TSV

      # Weights
      if (METHOD=="txt") {
        score = 0.5*D + 0.3*W + 0.2*R
      } else {
        score = 0.4*D + 0.2*W + 0.2*R + 0.2*C
      }

      printf("%.4f\n", clamp(score, 0, 1))
    }
  '
}

# Computes doc median reliability and pct of pages >= 0.5
# Args: pages_dir method
doc_reliability() {
  local pages_dir="$1" method="$2"
  # list page files sorted numerically
  # shellcheck disable=SC2012
  local scores
  scores="$(
    ls -1 "$pages_dir"/page-*.txt 2>/dev/null | sort -t- -k2,2n \
    | while read -r pf; do
        page_reliability "$(cat "$pf")" "$method"
      done
  )"
  if [[ -z "$scores" ]]; then
    echo "0.00 0.0"
    return 1
  fi
  # median + pct >= 0.5
  local median pgood
  median="$(printf '%s\n' "$scores" | sort -n | awk '{a[NR]=$1} END{ if(NR==0){print "0.00"} else if(NR%2==1){printf("%.2f",a[(NR+1)/2]);} else {printf("%.2f",(a[NR/2]+a[NR/2+1])/2);} }')"
  pgood="$(printf '%s\n' "$scores" | awk '{if($1>=0.5) c++} END{ if(NR==0) print "0.0"; else printf("%.1f",(100.0*c)/NR)}')"
  echo "$median $pgood"
}

write_outputs() { # (file csv out_dir method used_ocr counts.tsv) uses $PDF_WORKDIR/pages
  local file="$1" csv="$2" out_dir="$3" method="$4" used="$5" counts="$6"
  local bn base pages_csv; bn="$(basename -- "$file")"; base="${bn%.*}"; pages_csv="${out_dir}/${base}.pages.csv"
  local size_bytes; size_bytes="$(stat -c '%s' "$file" 2>/dev/null || stat -f '%z' "$file" 2>/dev/null || echo 0)"
  read -r pages_total good_pages total_chars coverage < <(summarize_counts "$counts")

  if should_paginate "$pages_total" "$size_bytes" "$total_chars"; then
    [ ! -s "$pages_csv" ] && printf 'filename,page,text,method,used_ocr\n' > "$pages_csv"
    while IFS=$'\t' read -r p c; do
      txt="$(cat "$PDF_WORKDIR/pages/page-${p}.txt" 2>/dev/null || true)"
      printf '"%s",%d,"%s","%s",%s\n' "$file" "$p" "$txt" "$method" "$used" >> "$pages_csv"
    done < "$counts"
    printf '"%s",1,"%s","%s",%s\n' "$file" "@pages_csv: ${base}.pages.csv" "$method" "$used" >> "$csv"
  else
    local combined=""; while IFS=$'\t' read -r p c; do
      txt="$(cat "$PDF_WORKDIR/pages/page-${p}.txt" 2>/dev/null || true)"
      [[ -n "$txt" ]] && combined="${combined}${combined:+\\n}${txt}"
    done < "$counts"
    printf '"%s",1,"%s","%s",%s\n' "$file" "$combined" "$method" "$used" >> "$csv"
  fi

  log_info "Wrote CSV for $bn (method=$method, used_ocr=$used, pages=$pages_total good=$good_pages cov=${coverage}%% total_chars=$total_chars)"
}
