********************************************************************************
* Redraw the formal placebo-window figure from its committed aggregate table.
* This does not require or expose the private review-level dataset.
*
* Usage from projects/steam-review-recovery/stata:
*   do 02_redraw_placebo_figure.do
********************************************************************************

version 16.0
clear all
set more off

local root "`c(pwd)'"
capture confirm file "`root'/output/tables/table_07_placebo_windows.csv"
if _rc {
    display as error "Run this file from projects/steam-review-recovery/stata."
    exit 601
}

import delimited using "`root'/output/tables/table_07_placebo_windows.csv", ///
    clear varnames(1) encoding(utf8)

gen cutoff_num = daily(cutoff_date, "YMD")
format cutoff_num %tdCCYY-NN-DD

set scheme s1color
capture graph set window fontface "Times New Roman"
twoway ///
    (scatter estimate cutoff_num if control == "English" & window_type == "placebo", ///
        mcolor(navy%65) msymbol(O) msize(small)) ///
    (scatter estimate cutoff_num if control == "English" & window_type != "placebo", ///
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

graph export "`root'/output/figures/figure_02_placebo_windows.png", replace width(2400)
display as result "Updated output/figures/figure_02_placebo_windows.png"
