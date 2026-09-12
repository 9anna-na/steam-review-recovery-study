********************************************************************************
* Why Did Reviews Recover Before the Fix?
* Reproducible Stata analysis of the 2024 Stardew Valley localization episode
*
* Usage from this directory:
*   do analysis.do 0     // full local data (preferred)
*   do analysis.do 1     // entirely synthetic public fixture
*
* The design is descriptive.  "Language-by-period comparison" is used instead
* of a causal DiD claim because parallel counterfactual trends are not proven.
********************************************************************************

version 16.0
clear all
set more off
set linesize 120
capture log close _all

args demo_mode
if "`demo_mode'" == "" local demo_mode 0

* Run the do-file from projects/steam-review-recovery/stata.
local root "`c(pwd)'"
capture confirm file "`root'/analysis.do"
if _rc {
    display as error "Run this file from projects/steam-review-recovery/stata."
    display as error "Example: cd .../platform-data-research-portfolio/projects/steam-review-recovery/stata"
    exit 601
}

global DATA "`root'/data"
if `demo_mode' == 1 global RUN_OUTPUT "`root'/output/synthetic"
else global RUN_OUTPUT "`root'/output"
global TABLES "$RUN_OUTPUT/tables"
global FIGURES "$RUN_OUTPUT/figures"
global LOGS "$RUN_OUTPUT/logs"

capture mkdir "`root'/output"
capture mkdir "$RUN_OUTPUT"
capture mkdir "$TABLES"
capture mkdir "$FIGURES"
capture mkdir "$LOGS"

log using "$LOGS/analysis.log", text replace

* esttab is used only for formatted regression tables.  The numeric CSV tables
* and figures below use official Stata commands and do not depend on add-ons.
capture which esttab
local have_esttab = (_rc == 0)
if !`have_esttab' {
    display as text "Optional package estout is absent. Install once with: ssc install estout"
}

********************************************************************************
* 1. Import and data audit
********************************************************************************

if `demo_mode' == 1 {
    local input "$DATA/synthetic/steam_reviews_synthetic.csv"
}
else {
    local input "$DATA/private/steam_reviews.csv"
}

capture confirm file "`input'"
if _rc {
    display as error "Input file not found: `input'"
    display as error "For a public test, generate the fixture and use: do analysis.do 1"
    exit 601
}

import delimited using "`input'", clear varnames(1) encoding(utf8) stringcols(3 4 5 6)

assert inlist(recommended, 0, 1)
assert inlist(language, 1, 2, 3, 4)
assert inlist(eventually_edited, 0, 1)

label define language_lbl 1 "English" 2 "Simplified Chinese" 3 "Spanish" 4 "Japanese"
label values language language_lbl

gen double created_at_tc = created_ms
gen double updated_at_tc = updated_ms
format created_at_tc updated_at_tc %tcCCYY-NN-DD_HH:MM:SS

gen review_date_num = daily(review_date, "YMD")
format review_date_num %tdCCYY-NN-DD

gen byte treat = language == 2
gen byte never_edited = created_ms == updated_ms
assert never_edited == 1 - eventually_edited

* This mirrors the small introductory command sequence in the learning brief.
* It is a tutorial specification, not the paper's preferred event definition.
gen byte post_may1 = review_date_num >= td(01may2024)
quietly regress recommended i.language##i.post_may1 if inlist(language, 1, 2), vce(robust)
estimates store tutorial_may1

* Exact public event timestamps, all in UTC.
scalar DAY_MS   = 24 * 60 * 60 * 1000
scalar HARMFUL  = clock("2024-04-18 20:08:40", "YMDhms")
scalar FORUM    = clock("2024-04-21 22:39:53", "YMDhms")
scalar DIRECT   = clock("2024-04-23 01:54:50", "YMDhms")
scalar LIVE     = clock("2024-04-26 19:39:05", "YMDhms")
scalar BASELINE = HARMFUL - 14 * DAY_MS
scalar POST_END = LIVE + 14 * DAY_MS

gen byte period = .
replace period = 0 if created_ms >= BASELINE & created_ms < HARMFUL
replace period = 1 if created_ms >= HARMFUL  & created_ms < LIVE
replace period = 2 if created_ms >= LIVE     & created_ms < POST_END
label define period_lbl 0 "14-day baseline" 1 "Disputed localization live" 2 "14 days after reversion"
label values period period_lbl

gen byte historical_safe = 0
replace historical_safe = 1 if period == 0 & updated_ms < HARMFUL
replace historical_safe = 1 if period == 1 & updated_ms < LIVE
replace historical_safe = 1 if period == 2 & updated_ms < POST_END

tempfile master
save `master', replace

********************************************************************************
* 2. Descriptive statistics
********************************************************************************

preserve
collapse (count) n_reviews=recommended ///
         (mean) recommend_rate=recommended edit_rate=eventually_edited ///
         (p50) median_playtime_hours=playtime_hours ///
         (mean) mean_playtime_hours=playtime_hours, by(language)
format recommend_rate edit_rate %9.4f
export delimited using "$TABLES/table_01_descriptive_statistics.csv", replace
restore

preserve
keep if never_edited & inlist(language, 1, 2) & period < .
collapse (count) n_reviews=recommended (mean) recommend_rate=recommended, by(period language)
format recommend_rate %9.4f
export delimited using "$TABLES/table_02_period_cells.csv", replace
restore

********************************************************************************
* 3. Main language-by-period models and robustness specifications
********************************************************************************

tempname results_handle
tempfile model_results
postfile `results_handle' str24 specification str14 control str24 contrast ///
    double estimate se ci_low ci_high p_value n_obs using `model_results', replace

estimates clear

* 3.1 Preferred model: English comparison, never-edited reviews.
use `master', clear
keep if never_edited & inlist(language, 1, 2) & period < .
replace treat = language == 2
quietly regress recommended i.treat##ib0.period, vce(robust)
estimates store lpm_en_never
local n = e(N)

quietly lincom 1.treat#1.period
post `results_handle' ("Never-edited primary") ("English") ("Damage vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period - 1.treat#1.period
post `results_handle' ("Never-edited primary") ("English") ("Recovery vs disputed") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period
post `results_handle' ("Never-edited primary") ("English") ("Post vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

* 3.2 Alternative comparison: combined Spanish and Latin-American Spanish.
use `master', clear
keep if never_edited & inlist(language, 2, 3) & period < .
replace treat = language == 2
quietly regress recommended i.treat##ib0.period, vce(robust)
estimates store lpm_es_never
local n = e(N)

quietly lincom 1.treat#1.period
post `results_handle' ("Never-edited primary") ("Spanish") ("Damage vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period - 1.treat#1.period
post `results_handle' ("Never-edited primary") ("Spanish") ("Recovery vs disputed") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period
post `results_handle' ("Never-edited primary") ("Spanish") ("Post vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

* 3.3 Naive final-state model.  This permits future edits to leak backward.
use `master', clear
keep if inlist(language, 1, 2) & period < .
replace treat = language == 2
quietly regress recommended i.treat##ib0.period, vce(robust)
estimates store lpm_en_final
local n = e(N)

quietly lincom 1.treat#1.period
post `results_handle' ("Final state naive") ("English") ("Damage vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period - 1.treat#1.period
post `results_handle' ("Final state naive") ("English") ("Recovery vs disputed") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

* 3.4 Period-end safeguard: admit a review only if its final update occurred
* before that historical period ended.
use `master', clear
keep if historical_safe & inlist(language, 1, 2) & period < .
replace treat = language == 2
quietly regress recommended i.treat##ib0.period, vce(robust)
estimates store lpm_en_safe
local n = e(N)

quietly lincom 1.treat#1.period
post `results_handle' ("Period-end safeguard") ("English") ("Damage vs baseline") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

quietly lincom 1.treat#2.period - 1.treat#1.period
post `results_handle' ("Period-end safeguard") ("English") ("Recovery vs disputed") ///
    (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p)) (`n')

postclose `results_handle'
use `model_results', clear
format estimate se ci_low ci_high %9.5f
export delimited using "$TABLES/table_03_model_contrasts.csv", replace

* A nonlinear sensitivity model.  Coefficients are log-odds, so the paper keeps
* the linear probability model as the most interpretable main presentation.
use `master', clear
keep if never_edited & inlist(language, 1, 2) & period < .
replace treat = language == 2
quietly logit recommended i.treat##ib0.period, vce(robust)
estimates store logit_en_never

if `have_esttab' {
    esttab lpm_en_never lpm_es_never lpm_en_final lpm_en_safe using ///
        "$TABLES/table_04_regression_models.rtf", replace ///
        b(4) se(4) label compress nogaps ///
        keep(1.treat#1.period 1.treat#2.period) ///
        mtitles("EN never edited" "ES never edited" "EN final state" "EN period safe") ///
        title("Language-by-period linear probability models")

    esttab logit_en_never using "$TABLES/table_05_logit_model.rtf", replace ///
        b(4) se(4) label compress nogaps ///
        keep(1.treat#1.period 1.treat#2.period) ///
        title("Logit sensitivity model")
}

********************************************************************************
* 4. Event-stage table and figure
********************************************************************************

use `master', clear
keep if never_edited & inlist(language, 1, 2)
replace treat = language == 2

gen byte stage = .
replace stage = 0 if created_ms >= BASELINE & created_ms < HARMFUL
replace stage = 1 if created_ms >= HARMFUL & created_ms < FORUM
replace stage = 2 if created_ms >= FORUM   & created_ms < DIRECT
replace stage = 3 if created_ms >= DIRECT  & created_ms < LIVE
replace stage = 4 if created_ms >= LIVE    & created_ms < LIVE + 7 * DAY_MS
keep if stage < .

label define stage_lbl 0 "Baseline" 1 "Patch live" 2 "Forum-to-message" ///
    3 "Message-to-reversion" 4 "Post-reversion"
label values stage stage_lbl

collapse (count) n=recommended (mean) rate=recommended ///
         (semean) se_rate=recommended, by(stage treat)
reshape wide n rate se_rate, i(stage) j(treat)

gen gap = rate1 - rate0
gen gap_se = sqrt(se_rate1^2 + se_rate0^2)
gen ci_low = gap - invnormal(.975) * gap_se
gen ci_high = gap + invnormal(.975) * gap_se
format rate0 rate1 gap ci_low ci_high %9.4f
export delimited using "$TABLES/table_06_event_stage_gaps.csv", replace

set scheme s1color
capture graph set window fontface "Times New Roman"
twoway ///
    (rcap ci_low ci_high stage, lcolor(gs7) lwidth(medthin)) ///
    (connected gap stage, mcolor(navy) lcolor(navy) msymbol(O) msize(medium)), ///
    yline(0, lcolor(gs9) lpattern(shortdash)) ///
    xlabel(0 "Baseline" 1 "Patch live" 2 "Forum-message" 3 "Message-reversion" 4 "Post", labsize(small)) ///
    xtitle("") ytitle("Simplified Chinese minus English recommendation rate") ///
    title("Recommendation gap across the event sequence", size(medsmall)) ///
    subtitle("Never-edited reviews; 95% confidence intervals", size(small)) ///
    legend(off) graphregion(color(white)) plotregion(color(white)) name(stage_gap, replace)
graph export "$FIGURES/figure_01_event_stage_gaps.png", replace width(2400)

********************************************************************************
* 5. Placebo windows
********************************************************************************

tempname placebo_handle
tempfile placebo_results
postfile `placebo_handle' str10 control str16 window_type double cutoff_date ///
    estimate se ci_low ci_high n_obs using `placebo_results', replace

foreach control_code in 1 3 {
    if `control_code' == 1 local control_name "English"
    if `control_code' == 3 local control_name "Spanish"

    foreach block in before after {
        if "`block'" == "before" {
            local first = td(25mar2024)
            local last  = td(10apr2024)
        }
        else {
            local first = td(05may2024)
            local last  = td(17may2024)
        }

        forvalues cutoff = `first'/`last' {
            use `master', clear
            keep if never_edited & inlist(language, 2, `control_code')
            keep if inrange(review_date_num, `cutoff' - 7, `cutoff' + 6)
            replace treat = language == 2
            gen byte placebo_post = review_date_num >= `cutoff'
            capture quietly regress recommended i.treat##i.placebo_post, vce(robust)
            if !_rc {
                local b = _b[1.treat#1.placebo_post]
                local s = _se[1.treat#1.placebo_post]
                local q = invttail(e(df_r), .025)
                local p = 2 * ttail(e(df_r), abs(`b' / `s'))
                post `placebo_handle' ("`control_name'") ("placebo") (`cutoff') ///
                    (`b') (`s') (`b' - `q' * `s') (`b' + `q' * `s') (e(N))
            }
        }
    }

    foreach focal in harm repair {
        if "`focal'" == "harm" local cutoff = td(18apr2024)
        else local cutoff = td(26apr2024)
        use `master', clear
        keep if never_edited & inlist(language, 2, `control_code')
        keep if inrange(review_date_num, `cutoff' - 7, `cutoff' + 6)
        replace treat = language == 2
        gen byte placebo_post = review_date_num >= `cutoff'
        quietly regress recommended i.treat##i.placebo_post, vce(robust)
        local b = _b[1.treat#1.placebo_post]
        local s = _se[1.treat#1.placebo_post]
        local q = invttail(e(df_r), .025)
        post `placebo_handle' ("`control_name'") ("focal_`focal'") (`cutoff') ///
            (`b') (`s') (`b' - `q' * `s') (`b' + `q' * `s') (e(N))
    }
}

postclose `placebo_handle'
use `placebo_results', clear
format cutoff_date %tdCCYY-NN-DD
format estimate se ci_low ci_high %9.5f
export delimited using "$TABLES/table_07_placebo_windows.csv", replace

twoway ///
    (scatter estimate cutoff_date if control == "English" & window_type == "placebo", ///
        mcolor(navy%65) msymbol(O) msize(small)) ///
    (scatter estimate cutoff_date if control == "English" & window_type != "placebo", ///
        mcolor(maroon) msymbol(D) msize(medlarge)), ///
    yline(0, lcolor(gs9) lpattern(shortdash)) ///
    xlabel(`=td(25mar2024)' "25 Mar" `=td(08apr2024)' "08 Apr" ///
        `=td(22apr2024)' "22 Apr" `=td(06may2024)' "06 May" ///
        `=td(17may2024)' "17 May", labsize(small)) ///
    xtitle("Candidate cutoff date", size(small)) ///
    ytitle("7-day language-by-window contrast", size(small)) ///
    title("Stable-period placebos versus focal cutoffs", size(medsmall)) ///
    subtitle("Simplified Chinese compared with English; never-edited reviews", size(small)) ///
    legend(order(1 "Stable placebo" 2 "Focal event") rows(1) size(small)) ///
    graphregion(color(white)) plotregion(color(white)) ///
    xsize(8) ysize(5) name(placebo_plot, replace)
graph export "$FIGURES/figure_02_placebo_windows.png", replace width(2400)

********************************************************************************
* 6. Review mutability diagnostic
********************************************************************************

use `master', clear
keep if inlist(language, 1, 2, 3)

scalar CRISIS_LENGTH = LIVE - HARMFUL
gen byte edit_period = .
replace edit_period = 0 if created_ms >= HARMFUL - CRISIS_LENGTH & created_ms < HARMFUL
replace edit_period = 1 if created_ms >= HARMFUL & created_ms < LIVE
replace edit_period = 2 if created_ms >= LIVE & created_ms < LIVE + CRISIS_LENGTH
keep if edit_period < .
label define edit_period_lbl 0 "Before" 1 "Disputed live" 2 "After reversion"
label values edit_period edit_period_lbl

collapse (count) n_reviews=eventually_edited (sum) n_edited=eventually_edited ///
         (mean) edit_rate=eventually_edited, by(edit_period language)
format edit_rate %9.4f
export delimited using "$TABLES/table_08_editing_rates.csv", replace

* --- prettier editing-rate figure: horizontal version ---
label define language_short 1 "EN" 2 "SC" 3 "ES", replace
label values language language_short

label define edit_period_short 0 "Before" 1 "Live" 2 "After", replace
label values edit_period edit_period_short

graph hbar edit_rate, ///
    over(language, label(labsize(small))) ///
    over(edit_period, label(labsize(small))) ///
    blabel(bar, format(%4.2f) size(small)) ///
    ytitle("Share eventually edited") ///
    title("Review mutability by language and creation cohort", size(medsmall)) ///
    subtitle("Final update timestamp only; prior versions unobserved", size(small)) ///
    bar(1, color(navy)) ///
    graphregion(color(white)) ///
    plotregion(color(white)) ///
    name(edit_plot, replace)

graph export "$FIGURES/figure_03_editing_rates.png", replace width(2400)
********************************************************************************
* 7. Reproducibility closeout
********************************************************************************

display as result "Analysis completed."
display as text "Tables:  $TABLES"
display as text "Figures: $FIGURES"
display as text "Log:     $LOGS/analysis.log"

log close
********************************************************************************
