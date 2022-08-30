### This is example R code you can use to print out a pedigree for your colony
### and do other fun things
library(dplyr)
library(kinship2)
library(jsonlite)

## this function transforms uuids into short 4-character strings. The odds of
## collision (i.e same id for multiple birds) are low but nonzero, so increase
## length from 4 if needed.
idfun <- function(name) { ifelse(is.na(name), NA, substring(name, 6)) }

## get the data and clean it up. Change the URL to match your server.
birds <- fromJSON(url("https://gracula.psyc.virginia.edu/birds/api/pedigree/?species=zebf")) %>%
    transmute(id=idfun(name), sire=idfun(sire), dam=idfun(dam), sex, alive)

## generate a pedigree
ped <- with(birds, pedigree(id=id, dadid=sire, momid=dam, sex=sex, status=!alive))
cairo_pdf("colony_pedigree.pdf", family="Helvetica", width=44, height=34)
plot(ped)
dev.off()

## figure out average relatedness to rest of colony
kin <- kinship(ped)
## trim out dead birds
ksmall <- kin[birds$alive, birds$alive]

## list unrelateds
ped.ur  <- pedigree.unrelated(ped, avail=birds$alive)
