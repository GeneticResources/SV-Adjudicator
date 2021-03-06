# RdTest
This repository contains the workflow that evaluates read coverage all CNV calls on a per-batch basis.

## Required matrics
Rd matrics (`{batch}.binCov.bed.gz` and `{batch}.binCov.median`) should be prepared for this process.  `{batch}.binCov.bed.gz` describes the coverage of each bin accross genome in each sample, and `{batch}.binCov.median` contians the median bincov coverage for each individual across whole genome.

To prepare this matrices:
1. Apply bincov on each individual, either with or without genomic blacklist
2. Concatinate bincov calls of all individuals to form {batch}.binCov.bed
3. bgzip and tabix the concatinated bed.

The bed file look like:
```
#chr start end sample1 sample2 sample3 sample4
1 10000 10100 938 1387 954 1344
1 10100 10200 1089 1462 927 1365
1 10200 10300 554 694 462 679
1 10300 10400 1149 1473 1019 1458
1 10400 10500 767 964 649 880
1 10500 10600 43 102 81 38
1 10600 10700 16 40 32 21
1 10700 10800 0 1 1 1
1 10800 10900 4 0 3 21
```

## Process through snakemake
Just type `snakemake` under this directory and the RdTest workflow with be autonamously processed.

## Module configuration and input
The configuration file `config.yaml` outlines the module's inputs and parameters, and should be modified accordingly to each specific project. 

* `batches` : filepath
Sample/group/batch key.

* `input_vcfs` : vcf files to be processed in this step. 
The vcf files are produced through `01_algorithm_integration` and are kept under `../../01_algorithm_integration/vcfcluster`

* `input_beds` : vcf files to be processed in this step. 
The bed files are produced through `01_algorithm_integration` and are kept under `../../01_algorithm_integration/rdtest_beds`

* `groups` : list of samples to be processed.

* `chromos` : list of chromosomes to be processed.
This file should be modified according to different reference genome. It is recommended that autosomes and allosomes are prepared differently.

* `pesr_sources` : 
Names of pair end/split read algorithms to be processed

* `depth_sources` :
Names of read depth algorithms to be processed

* `rdtest`: script to process RdTest
This manuscript is kept at: scripts/RdTest.R

* `coveragefile` : the matrices describing the coverage of each bin accross genome in each sample
`{batch}.binCov.bed.gz`

* `medianfile` : the metrics describing the medeian read coverage of each sample accross whole genome
`{batch}.binCov.median`

* `famfile` : ../../ref/{batch}.fam
This file describes the family structure in batch

* rdtest_split_size: 100 by default
This number specifies the number of CNVs included in each sub-bed that'll be processed by RdTest.R 

## Process each step manually
It is also possible to run each step in this module manually, by following these steps:

1. Randomly split the big bed file into small beds for faster processing:
```
python scripts/split_rdtest_random.py ../../01_algorithm_integration/rdtest_beds/{batch}.{source}.{chrom}.bed split_beds/{batch}.{source}.{chrom}. -s number_SVs_per_bed
```
Output from this step are `{batch}.{source}.{chrom}.XXX`, where XXX are numbers differentiating each sub-file.

2. Run RdTest. In this step, samples should be split by sex to have chromosome X and Y processed. 

Check and install R packages required for rdtest:
```
Rscript scripts/Rpackage_check.R
``` 

For **autosomes**:

```
Rscript scripts/RdTest.R -b split_beds/{batch}.{source}.{chrom}.XXX -o split_rdtest/ -n {batch}.{source}.{chrom}.XXX -c {batch}.binCov.bed.gz -m {batch}.binCov.median -f full_sample_list.fam
```

For **allosomes**, a female whitelist containing full list of all females samples and a male list with names of all males samples should be prepared:
```
Rscript ./scripts/RdTest.R -b split_beds/{batch}.{source}.{chrom}.XXX -o split_rdtest/ -n {batch}.{source}.{chrom}.XXX.females -w female.whitelist  -c {batch}.binCov.bed.gz -m {batch}.binCov.median -f full_sample_list.fam
Rscript ./scripts/RdTest.R -b split_beds/{batch}.{source}.{chrom}.XXX -o split_rdtest/ -n {batch}.{source}.{chrom}.XXX.males -w male.whitelist  -c {batch}.binCov.bed.gz -m {batch}.binCov.median -f full_sample_list.fam
```

3. Concatinate the sub metrics:
```
bash scripts/rdtest_mergesplit.sh {batch} {source} {chrom}
```


## Output files
Output files include RdTest scores for each CNV, are kept under `rdtest/`:
* `rdtest/{batch}.{source}.{chrom}.metrics`

