# Using DeepTrio for small variant calling from the trio sequenced with PacBio HiFi

In this case study, we describe applying [DeepTrio](deeptrio-details.md) to a
real PacBio WGS trio. Then we assess the quality of the DeepTrio variant calls
with `hap.py`. In addition we evaluate a Mendelian violation rate for a merged
VCF.

To make it faster to run over this case study, we run only on chromosome 20.


## Prepare environment

### Tools

[Docker](https://docs.docker.com/get-docker/) will be used to run DeepTrio and
[hap.py](https://github.com/illumina/hap.py),

### Download Reference

We will be using GRCh38 for this case study.

```bash
mkdir -p reference

FTPDIR=ftp://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/001/405/GCA_000001405.15_GRCh38/seqs_for_alignment_pipelines.ucsc_ids

curl ${FTPDIR}/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.gz | gunzip > reference/GRCh38_no_alt_analysis_set.fasta
curl ${FTPDIR}/GCA_000001405.15_GRCh38_no_alt_analysis_set.fna.fai > reference/GRCh38_no_alt_analysis_set.fasta.fai
```

### Download Genome in a Bottle Benchmarks

We will benchmark our variant calls against v4.2.1 of the Genome in a Bottle
small variant benchmarks for HG002, HG003, and HG004 trio.

```bash
mkdir -p benchmark

FTPDIR=ftp://ftp-trace.ncbi.nlm.nih.gov/giab/ftp/release/AshkenazimTrio

curl ${FTPDIR}/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed > benchmark/HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed
curl ${FTPDIR}/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz > benchmark/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz
curl ${FTPDIR}/HG002_NA24385_son/NISTv4.2.1/GRCh38/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi > benchmark/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi

curl ${FTPDIR}/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed > benchmark/HG003_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed
curl ${FTPDIR}/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz > benchmark/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz
curl ${FTPDIR}/HG003_NA24149_father/NISTv4.2.1/GRCh38/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi > benchmark/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi

curl ${FTPDIR}/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed > benchmark/HG004_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed
curl ${FTPDIR}/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz > benchmark/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz
curl ${FTPDIR}/HG004_NA24143_mother/NISTv4.2.1/GRCh38/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi > benchmark/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz.tbi
```

### Download HG002, HG003, and HG004 BAM files

We'll use HG002, HG003, HG004 PacBio HiFi WGS reads publicly available from the
[PrecisionFDA Truth v2 Challenge](https://precision.fda.gov/challenges/10).
These reads have been aligned to the GRCh38_no_alt_analysis reference using
[pbmm2](https://github.com/PacificBiosciences/pbmm2).

```bash
mkdir -p input
HTTPDIR=https://storage.googleapis.com/deepvariant/pacbio-case-study-testdata

curl ${HTTPDIR}/HG002.pfda_challenge.grch38.phased.chr20.bam > input/HG002.pfda_challenge.grch38.phased.chr20.bam
curl ${HTTPDIR}/HG002.pfda_challenge.grch38.phased.chr20.bam.bai > input/HG002.pfda_challenge.grch38.phased.chr20.bam.bai

curl ${HTTPDIR}/HG003.pfda_challenge.grch38.phased.chr20.bam > input/HG003.pfda_challenge.grch38.phased.chr20.bam
curl ${HTTPDIR}/HG003.pfda_challenge.grch38.phased.chr20.bam.bai > input/HG003.pfda_challenge.grch38.phased.chr20.bam.bai

curl ${HTTPDIR}/HG004.pfda_challenge.grch38.phased.chr20.bam > input/HG004.pfda_challenge.grch38.phased.chr20.bam
curl ${HTTPDIR}/HG004.pfda_challenge.grch38.phased.chr20.bam.bai > input/HG004.pfda_challenge.grch38.phased.chr20.bam.bai
```

## Running DeepTrio with one command

DeepTrio pipeline consists of 4 steps: `make_examples`, `call_variants`,
`postprocess_variants` and `GLnexus merge`. It is possible to run the first
three steps with one command using the `run_deeptrio` script. GLnexus
is run as a separate command.

### Running on a CPU-only machine

```bash
mkdir -p output
mkdir -p output/intermediate_results_dir

BIN_VERSION="1.2.0"

sudo apt -y update
sudo apt-get -y install docker.io
sudo docker pull google/deepvariant:deeptrio-"${BIN_VERSION}"

time sudo docker run \
  -v "${PWD}/input":"/input" \
  -v "${PWD}/output":"/output" \
  -v "${PWD}/reference":"/reference" \
  google/deepvariant:deeptrio-"${BIN_VERSION}" \
  /opt/deepvariant/bin/deeptrio/run_deeptrio \
  --model_type PACBIO \
  --ref /reference/GRCh38_no_alt_analysis_set.fasta \
  --reads_child /input/HG002.pfda_challenge.grch38.phased.chr20.bam \
  --reads_parent1 /input/HG003.pfda_challenge.grch38.phased.chr20.bam \
  --reads_parent2 /input/HG004.pfda_challenge.grch38.phased.chr20.bam \
  --output_vcf_child /output/HG002.output.vcf.gz \
  --output_vcf_parent1 /output/HG003.output.vcf.gz \
  --output_vcf_parent2 /output/HG004.output.vcf.gz \
  --sample_name_child 'HG002' \
  --sample_name_parent1 'HG003' \
  --sample_name_parent2 'HG004' \
  --num_shards $(nproc) \
  --intermediate_results_dir /output/intermediate_results_dir \
  --output_gvcf_child /output/HG002.g.vcf.gz \
  --output_gvcf_parent1 /output/HG003.g.vcf.gz \
  --output_gvcf_parent2 /output/HG004.g.vcf.gz \
  --regions chr20 \
  --use_hp_information
```

The `--use_hp_information` arg makes use of a phased reads, thus allowing a
further improvement of the accuracy. In order to use this feature input BAM
files have to be phased. For the detailed description on how to do that please
see [DeepVariant PacBio case study](deepvariant-pacbio-model-case-study.md).

By specifying `--model_type PACBIO`, you'll be using a model that is best suited
for PacBio HiFi Whole Genome Sequencing data.

`--intermediate_results_dir` flag is optional. By specifying it, the
intermediate outputs of `make_examples` and `call_variants` stages can be found
in the directory. After the command, you can find these files in the directory:

```
call_variants_output_child.tfrecord.gz
call_variants_output_parent1.tfrecord.gz
call_variants_output_parent2.tfrecord.gz

gvcf_child.tfrecord-?????-of-?????.gz
gvcf_parent1.tfrecord-?????-of-?????.gz
gvcf_parent2.tfrecord-?????-of-?????.gz

make_examples_child.tfrecord-?????-of-?????.gz
make_examples_parent1.tfrecord-?????-of-?????.gz
make_examples_parent2.tfrecord-?????-of-?????.gz
```

For running on GPU machines, or using Singularity instead of Docker, see
[Quick Start](deepvariant-quick-start.md) or
[DeepVariant PacBio case study](deepvariant-pacbio-model-case-study.md).

## Merge VCFs using GLnexus

At this step we take all 3 VCFs generated in the previous step and merge them
using GLnexus.

```bash
sudo docker pull quay.io/mlin/glnexus:v1.2.7

# bcftools and bgzip are now included in our docker images.
# You can also install them separately.
sudo docker run \
  -v "${PWD}/output":"/output" \
  quay.io/mlin/glnexus:v1.2.7 \
  /usr/local/bin/glnexus_cli \
  --config DeepVariant_unfiltered \
  /output/HG002.g.vcf.gz \
  /output/HG003.g.vcf.gz \
  /output/HG004.g.vcf.gz \
  | sudo docker run -i google/deepvariant:deeptrio-"${BIN_VERSION}" \
    bcftools view - \
  | sudo docker run -i google/deepvariant:deeptrio-"${BIN_VERSION}" \
    bgzip -c > output/HG002_trio_merged.vcf.gz
```

After completion of GLnexus command we should have a new merged VCF file in the
output directory.

```
HG002_trio_merged.vcf.gz
```

## Benchmark on chr20

### Calculate Mendelian Violation rate

```bash
sudo docker pull realtimegenomics/rtg-tools

sudo docker run \
  -v "${PWD}/input":"/input" \
  -v "${PWD}/reference":"/reference" \
  realtimegenomics/rtg-tools format \
  -o /reference/GRCh38_no_alt_analysis_set.sdf "/reference/GRCh38_no_alt_analysis_set.fasta"

FILE="reference/trio.ped"
cat <<EOM >$FILE
#PED format pedigree
#
#fam-id/ind-id/pat-id/mat-id: 0=unknown
#sex: 1=male; 2=female; 0=unknown
#phenotype: -9=missing, 0=missing; 1=unaffected; 2=affected
#
#fam-id ind-id pat-id mat-id sex phen
1 HG002 HG003 HG004 1 0
1 HG003 0 0 1 0
1 HG004 0 0 2 0
EOM

sudo docker run \
-v "${PWD}/input":"/input" \
-v "${PWD}/reference":"/reference" \
-v "${PWD}/output":"/output" \
realtimegenomics/rtg-tools mendelian \
-i "/output/HG002_trio_merged.vcf.gz" \
-o "/output/HG002_trio_annotated.output.vcf.gz" \
--pedigree=/reference/trio.ped \
-t /reference/GRCh38_no_alt_analysis_set.sdf \
| tee output/deepvariant.input_rtg_output.txt
```

As a result we should get the following output:

```bash
Checking: /output/HG002_trio_merged.vcf.gz
Family: [HG003 + HG004] -> [HG002]
122 non-pass records were skipped
Concordance HG002: F:147733/148927 (99.20%)  M:148440/149072 (99.58%)  F+M:144203/146434 (98.48%)
Sample HG002 has less than 99.0 concordance with both parents. Check for incorrect pedigree or sample mislabelling.
0/157768 (0.00%) records did not conform to expected call ploidy
155055/157768 (98.28%) records were variant in at least 1 family member and checked for Mendelian constraints
7942/155055 (5.12%) records had indeterminate consistency status due to incomplete calls
2646/155055 (1.71%) records contained a violation of Mendelian constraints
```

### Benchmark variant calls against 4.2.1 truth set with hap.py

```bash
mkdir -p happy

sudo docker pull jmcdani20/hap.py:v0.3.12

sudo docker run \
  -v "${PWD}/benchmark":"/benchmark" \
  -v "${PWD}/input":"/input" \
  -v "${PWD}/output":"/output" \
  -v "${PWD}/reference":"/reference" \
  -v "${PWD}/happy:/happy" \
  jmcdani20/hap.py:v0.3.12 /opt/hap.py/bin/hap.py \
  /benchmark/HG002_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
  /output/HG002.output.vcf.gz \
  -f /benchmark/HG002_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed \
  -r /reference/GRCh38_no_alt_analysis_set.fasta \
  -o /happy/HG002.output \
  --engine=vcfeval \
  --pass-only \
  -l chr20

sudo docker run \
  -v "${PWD}/benchmark":"/benchmark" \
  -v "${PWD}/input":"/input" \
  -v "${PWD}/output":"/output" \
  -v "${PWD}/reference":"/reference" \
  -v "${PWD}/happy:/happy" \
  jmcdani20/hap.py:v0.3.12 /opt/hap.py/bin/hap.py \
  /benchmark/HG003_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
  /output/HG003.output.vcf.gz \
  -f /benchmark/HG003_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed \
  -r /reference/GRCh38_no_alt_analysis_set.fasta \
  -o /happy/HG003.output \
  --engine=vcfeval \
  --pass-only \
  -l chr20

sudo docker run \
  -v "${PWD}/benchmark":"/benchmark" \
  -v "${PWD}/input":"/input" \
  -v "${PWD}/output":"/output" \
  -v "${PWD}/reference":"/reference" \
  -v "${PWD}/happy:/happy" \
  jmcdani20/hap.py:v0.3.12 /opt/hap.py/bin/hap.py \
  /benchmark/HG004_GRCh38_1_22_v4.2.1_benchmark.vcf.gz \
  /output/HG004.output.vcf.gz \
  -f /benchmark/HG004_GRCh38_1_22_v4.2.1_benchmark_noinconsistent.bed \
  -r /reference/GRCh38_no_alt_analysis_set.fasta \
  -o /happy/HG004.output \
  --engine=vcfeval \
  --pass-only \
  -l chr20
```

```
Benchmarking Summary for HG002:
Type Filter  TRUTH.TOTAL  TRUTH.TP  TRUTH.FN  QUERY.TOTAL  QUERY.FP  QUERY.UNK  FP.gt  FP.al  METRIC.Recall  METRIC.Precision  METRIC.Frac_NA  METRIC.F1_Score  TRUTH.TOTAL.TiTv_ratio  QUERY.TOTAL.TiTv_ratio  TRUTH.TOTAL.het_hom_ratio  QUERY.TOTAL.het_hom_ratio
INDEL    ALL        11256     11228        28        23098        66      11328     16     47       0.997512          0.994393        0.490432         0.995950                     NaN                     NaN                   1.561710                   2.296831
INDEL   PASS        11256     11228        28        23098        66      11328     16     47       0.997512          0.994393        0.490432         0.995950                     NaN                     NaN                   1.561710                   2.296831
  SNP    ALL        71333     71270        63        98167        25      26797     21      4       0.999117          0.999650        0.272974         0.999383                2.314904                1.960488                   1.715978                   2.007482
  SNP   PASS        71333     71270        63        98167        25      26797     21      4       0.999117          0.999650        0.272974         0.999383                2.314904                1.960488                   1.715978                   2.007482

Benchmarking Summary for HG003:
Type Filter  TRUTH.TOTAL  TRUTH.TP  TRUTH.FN  QUERY.TOTAL  QUERY.FP  QUERY.UNK  FP.gt  FP.al  METRIC.Recall  METRIC.Precision  METRIC.Frac_NA  METRIC.F1_Score  TRUTH.TOTAL.TiTv_ratio  QUERY.TOTAL.TiTv_ratio  TRUTH.TOTAL.het_hom_ratio  QUERY.TOTAL.het_hom_ratio
INDEL    ALL        10628     10597        31        22160        58      11011     20     36       0.997083          0.994798        0.496886         0.995939                     NaN                     NaN                   1.748961                   2.514173
INDEL   PASS        10628     10597        31        22160        58      11011     20     36       0.997083          0.994798        0.496886         0.995939                     NaN                     NaN                   1.748961                   2.514173
  SNP    ALL        70166     70143        23        92524        21      22304     12      3       0.999672          0.999701        0.241062         0.999687                2.296566                1.999125                   1.883951                   2.079418
  SNP   PASS        70166     70143        23        92524        21      22304     12      3       0.999672          0.999701        0.241062         0.999687                2.296566                1.999125                   1.883951                   2.079418

Benchmarking Summary for HG004:
Type Filter  TRUTH.TOTAL  TRUTH.TP  TRUTH.FN  QUERY.TOTAL  QUERY.FP  QUERY.UNK  FP.gt  FP.al  METRIC.Recall  METRIC.Precision  METRIC.Frac_NA  METRIC.F1_Score  TRUTH.TOTAL.TiTv_ratio  QUERY.TOTAL.TiTv_ratio  TRUTH.TOTAL.het_hom_ratio  QUERY.TOTAL.het_hom_ratio
INDEL    ALL        11000     10957        43        22500        59      10974     21     37       0.996091          0.994881        0.487733         0.995486                     NaN                     NaN                   1.792709                   2.520783
INDEL   PASS        11000     10957        43        22500        59      10974     21     37       0.996091          0.994881        0.487733         0.995486                     NaN                     NaN                   1.792709                   2.520783
  SNP    ALL        71659     71587        72        93846        34      22141     11     12       0.998995          0.999526        0.235929         0.999260                2.310073                2.018713                   1.878340                   1.972145
  SNP   PASS        71659     71587        72        93846        34      22141     11     12       0.998995          0.999526        0.235929         0.999260                2.310073                2.018713                   1.878340                   1.972145
```
