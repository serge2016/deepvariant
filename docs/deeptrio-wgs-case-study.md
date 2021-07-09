# DeepTrio whole genome sequencing case study

In this case study, we describe applying DeepTrio to a real WGS trio. Then we
assess the quality of the DeepTrio variant calls with `hap.py`. In addition we
evaluate a mendelian violation rate for a merged VCF.

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

We'll use HG002, HG003, HG004 Illumina WGS reads publicly available from the
[PrecisionFDA Truth v2 Challenge](https://precision.fda.gov/challenges/10).

```bash
mkdir -p input
HTTPDIR=https://storage.googleapis.com/deepvariant/case-study-testdata

curl ${HTTPDIR}/HG002.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam > input/HG002.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam
curl ${HTTPDIR}/HG002.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai > input/HG002.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai

curl ${HTTPDIR}/HG003.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam > input/HG003.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam
curl ${HTTPDIR}/HG003.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai > input/HG003.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai

curl ${HTTPDIR}/HG004.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam > input/HG004.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam
curl ${HTTPDIR}/HG004.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai > input/HG004.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam.bai
```

## Running DeepTrio with one command

DeepTrio pipeline consists of 4 steps: `make_examples`, `call_variants`,
`postprocess_variants` and `GLnexus merge`. It is possible to run DeepTrio with
one command using the `run_deepvariant` script. GLnexus is run as a separate
command.

### Running on a CPU-only machine

```bash
mkdir -p output
mkdir -p output/intermediate_results_dir

BIN_VERSION=1.1.0

time sudo docker run \
  -v "${PWD}/input":"/input"   \
  -v "${PWD}/output":"/output"  \
  -v "${PWD}/reference":"/reference" \
  google/deepvariant:deeptrio-"${BIN_VERSION}" \
  /opt/deepvariant/bin/deeptrio/run_deeptrio \
  --model_type WGS \
  --ref /reference/GRCh38_no_alt_analysis_set.fasta \
  --reads_child /input/HG002.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam \
  --reads_parent1 /input/HG003.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam \
  --reads_parent2 /input/HG004.novaseq.pcr-free.35x.dedup.grch38_no_alt.chr20.bam \
  --output_vcf_child /output/HG002.output.vcf.gz \
  --output_vcf_parent1 /output/HG003.output.vcf.gz \
  --output_vcf_parent2 /output/HG004.output.vcf.gz \
  --sample_name_child 'HG002' \
  --sample_name_parent1 'HG003' \
  --sample_name_parent2 'HG004' \
  --num_shards $(nproc)  \
  --regions chr20 \
  --intermediate_results_dir /output/intermediate_results_dir \
  --output_gvcf_child /output/HG002.g.vcf.gz \
  --output_gvcf_parent1 /output/HG003.g.vcf.gz \
  --output_gvcf_parent2 /output/HG004.g.vcf.gz
```

By specifying `--model_type WGS`, you'll be using a model that is best suited
for Illumina Whole Genome Sequencing data.

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
[Quick Start](deepvariant-quick-start.md).

## Merge VCFs using GLnexus

At this step we take all 3 VCFs generated in the previous step and merge them
using GLnexus.

```bash
# BCFTools are required:
sudo apt-get -y install bcftools
sudo apt-get -y install tabix

sudo docker run \
  -v "${PWD}/output":"/output" \
  quay.io/mlin/glnexus:v1.2.7 \
  /usr/local/bin/glnexus_cli \
  --config DeepVariantWGS \
  /output/HG002.g.vcf.gz \
  /output/HG003.g.vcf.gz \
  /output/HG004.g.vcf.gz \
  | bcftools view - | bgzip -c > output/HG002_trio_merged.vcf.gz
```

After completion of GLnexus command we should have a new merged VCF file in the
output directory.

```
HG002_trio_merged.vcf.gz
```

## Benchmark on chr20

### Calculate mendelian vialation rate

```bash
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
35 non-pass records were skipped
Concordance HG002: F:133992/134497 (99.62%)  M:134059/134588 (99.61%)  F+M:132670/133643 (99.27%)
0/137097 (0.00%) records did not conform to expected call ploidy
136009/137097 (99.21%) records were variant in at least 1 family member and checked for Mendelian constraints
2022/136009 (1.49%) records had indeterminate consistency status due to incomplete calls
1058/136009 (0.78%) records contained a violation of Mendelian constraints
```

### Perform analysis with hap.py against 4.2.1 truth set

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
INDEL    ALL        11256     11208        48        21259        18       9601     11      6       0.995736          0.998456        0.451620         0.997094                     NaN                     NaN                   1.561710                   2.070802
INDEL   PASS        11256     11208        48        21259        18       9601     11      6       0.995736          0.998456        0.451620         0.997094                     NaN                     NaN                   1.561710                   2.070802
  SNP    ALL        71333     71064       269        87357        29      16213      4      4       0.996229          0.999592        0.185595         0.997908                2.314904                2.053626                   1.715978                   1.712794
  SNP   PASS        71333     71064       269        87357        29      16213      4      4       0.996229          0.999592        0.185595         0.997908                2.314904                2.053626                   1.715978                   1.712794

Benchmarking Summary for HG003:
Type Filter  TRUTH.TOTAL  TRUTH.TP  TRUTH.FN  QUERY.TOTAL  QUERY.FP  QUERY.UNK  FP.gt  FP.al  METRIC.Recall  METRIC.Precision  METRIC.Frac_NA  METRIC.F1_Score  TRUTH.TOTAL.TiTv_ratio  QUERY.TOTAL.TiTv_ratio  TRUTH.TOTAL.het_hom_ratio  QUERY.TOTAL.het_hom_ratio
INDEL    ALL        10628     10579        49        21062        19      10002     14      5       0.995390          0.998282        0.474884         0.996834                     NaN                     NaN                   1.748961                   2.247423
INDEL   PASS        10628     10579        49        21062        19      10002     14      5       0.995390          0.998282        0.474884         0.996834                     NaN                     NaN                   1.748961                   2.247423
  SNP    ALL        70166     69929       237        85198        51      15193     18      7       0.996622          0.999271        0.178326         0.997945                2.296566                2.069257                   1.883951                   1.874380
  SNP   PASS        70166     69929       237        85198        51      15193     18      7       0.996622          0.999271        0.178326         0.997945                2.296566                2.069257                   1.883951                   1.874380

Benchmarking Summary for HG004:
Type Filter  TRUTH.TOTAL  TRUTH.TP  TRUTH.FN  QUERY.TOTAL  QUERY.FP  QUERY.UNK  FP.gt  FP.al  METRIC.Recall  METRIC.Precision  METRIC.Frac_NA  METRIC.F1_Score  TRUTH.TOTAL.TiTv_ratio  QUERY.TOTAL.TiTv_ratio  TRUTH.TOTAL.het_hom_ratio  QUERY.TOTAL.het_hom_ratio
INDEL    ALL        11000     10950        50        21471        25      10007     17      6       0.995455          0.997819        0.466071         0.996636                     NaN                     NaN                   1.792709                   2.318601
INDEL   PASS        11000     10950        50        21471        25      10007     17      6       0.995455          0.997819        0.466071         0.996636                     NaN                     NaN                   1.792709                   2.318601
  SNP    ALL        71659     71428       231        86303        45      14785     10      6       0.996776          0.999371        0.171315         0.998072                2.310073                2.071909                   1.878340                   1.772111
  SNP   PASS        71659     71428       231        86303        45      14785     10      6       0.996776          0.999371        0.171315         0.998072                2.310073                2.071909                   1.878340                   1.772111
```