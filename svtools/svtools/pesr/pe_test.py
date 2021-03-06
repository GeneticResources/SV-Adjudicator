#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2017 Matthew Stone <mstone5@mgh.harvard.edu>
# Distributed under terms of the MIT license.

"""

"""

from collections import defaultdict
import numpy as np
import pandas as pd
import pysam
from .pesr_test import PESRTest, PESRTestRunner


class _DiscPair:
    def __init__(self, chrA, posA, strandA, chrB, posB, strandB, sample):
        self.chrA = chrA
        self.posA = int(posA)
        self.strandA = strandA
        self.chrB = chrB
        self.posB = int(posB)
        self.strandB = strandB
        self.sample = sample


class PETest(PESRTest):
    def __init__(self, discfile, window_in=50, window_out=500):
        self.discfile = discfile
        self.window_in = window_in
        self.window_out = window_out

        super().__init__()

    def test_record(self, record, called, background):
        # Test SR support at all coordinates within window of start/end
        results = self.test(record, self.window_in, self.window_out,
                            called, background)

        results = results.to_frame().transpose()

        # Clean up columns
        results['name'] = record.id
        cols = 'name log_pval called background'.split()

        return results[cols]

    def test(self, record, window_in, window_out, called, background):
        """
        Test enrichment of discordant reads in a set of samples.

        Arguments
        ---------
        record : pysam.VariantFile
        window_in : int
        window_out : int
        called : list of str
            List of called samples to test
        background : list of str
            List of samples to use as background

        Returns
        -------
        called_median : float
        background_median : float
        log_pval : float
            Negative log10 p-value
        """

        # Load split counts.
        counts = self.load_counts(record, window_in, window_out)
        return super().test(counts, called, background)

    def load_counts(self, record, window_in, window_out):
        """Load pandas DataFrame from tabixfile"""

        def _get_coords(pos, strand):
            if strand == '+':
                start, end = pos - window_out, pos + window_in
            else:
                start, end = pos - window_in, pos + window_out
            return start, end

        strandA, strandB = record.info['STRANDS']
        startA, endA = _get_coords(record.pos, strandA)
        startB, endB = _get_coords(record.stop, strandB)

        region = '{0}:{1}-{2}'.format(record.chrom, startA, endA)
        pairs = self.discfile.fetch(region=region, parser=pysam.asTuple())

        counts = defaultdict(int)
        for pair in pairs:
            pair = _DiscPair(*pair)

            # Pairs were selected based on window around chrA;
            # just need to check chrB
            if pair.chrB != record.info['CHR2']:
                continue
            if not (startB <= pair.posB < endB):
                continue

            # Require pairs match breakpoint strand
            if pair.strandA != strandA or pair.strandB != strandB:
                continue

            counts[pair.sample] += 1

        counts = pd.DataFrame.from_dict({'count': counts})
        counts = counts.reset_index()
        counts = counts.rename(columns={'index': 'sample'})

        return counts


class PETestRunner(PESRTestRunner):
    def __init__(self, vcf, discfile, fout, n_background=752,
                 window_in=50, window_out=500,
                 whitelist=None, blacklist=None):
        """
        vcf : pysam.VariantFile
        discfile : pysam.TabixFile
        """
        self.petest = PETest(discfile, window_in, window_out)
        self.fout = fout

        super().__init__(vcf, n_background, whitelist, blacklist)
    def null_score(self,record, null_val=0.0):
        """Null score if no clipped reads observed"""
        score = pd.Series([null_val] * 3, ['background', 'called', 'log_pval']).rename('count') # not sure what count is
        score.index.name = 'status' # also not sure what this is
        score['name']=record.id
        count=score.to_frame().transpose()
        cols = 'name log_pval called background'.split()
        return count[cols]

    def test_record(self, record):
        if not self._strand_check(record):
            counts = self.petest.null_score(null_val='NA')
        else:
            called, background = self.choose_background(record)
            if called==[] or background==[]:     
                   counts = self.null_score(record,null_val='NA')
            else:  
                   counts = self.petest.test_record(record, called, background )
        print(counts)    
        counts = counts.rename(columns={'called': 'called_median',
                                        'background': 'bg_median'})
        counts.to_csv(self.fout, header=False, index=False,
                      sep='\t', na_rep='NA')

    @staticmethod
    def _strand_check(record):
        return ('STRANDS' in record.info.keys() and
                record.info['STRANDS'] in '++ +- -+ --'.split())
