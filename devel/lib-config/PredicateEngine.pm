package PredicateEngine;

use Exporter;
@ISA = qw(Exporter);
@EXPORT = qw(%values policy_check);

my $P = $::P;
my $P0 = $::P0;

use strict;

our %values;

# Predicate execution engine.
my %pred_attr;
sub pred_do {
	my ($pred) = @_;
	my (@a) = split(' ', $pred);
	my $possible;

	if ($a[0] eq 'arch') {
		die "$P: $pred: malformed -- $pred <arch>\n" if ($#a < 1);
		for $possible (@a[1..$#a]) {
			#print "    *** ARCH<$flavour ?? $possible>\n";
			return 1 if ($pred_attr{'arch'} eq $possible);
		}
		return 0;
	} elsif ($a[0] eq 'flavour') {
		die "$P: $pred: malformed -- $pred <flavour>\n" if ($#a < 1);
		for $possible (@a[1..$#a]) {
			#print "    *** FLAVOUR<$flavour ?? $a[1]>\n";
			return 1 if ($pred_attr{'flavour'} eq $possible);
		}
		return 0;
	} elsif ($a[0] eq 'value') {
		@a = ($a[0], $pred_attr{'option'}, @a[1..$#a]) if ($#a == 1);
		die "$P: $pred: malformed -- $pred <name> <val>\n" if ($#a != 2);
		#warn "    *** CHECK<$a[1] $a[2] ?? " . $values{$pred_attr{'column'}, $a[1]} . ">\n";
		return ($values{$pred_attr{'column'}, $a[1]} eq $a[2]);
	} elsif ($a[0] eq 'exists') {
		@a = ($a[0], $pred_attr{'option'}, @a[1..$#a]) if ($#a == 1);
		die "$P: $pred: malformed -- $pred <name>\n" if ($#a != 1);
		return (defined $values{$pred_attr{'column'}, $a[1]});
	} else {
		die "$P: $pred: unknown predicate\n";
	}
	return 1;
}
sub pred_first {
	my ($rest) = @_;
	my $depth = 0;
	my $off;
	my $char;
	my $pred;
	
	for ($off = 0; $off <= length($rest); $off++) {
		$char = substr($rest, $off, 1);
		if ($char eq '(') {
			$depth++;
		} elsif ($char eq ')') {
			$depth--;
		} elsif ($depth == 0 && $char eq '&') {
			last;
		} elsif ($depth == 0 && $char eq '|') {
			last;
		}
	}
	if ($depth > 0) {
		die "$P: $rest: missing close parenthesis ')'\n";
	} elsif ($depth < 0) {
		die "$P: $rest: missing open parenthesis '('\n";
	}

	($pred, $rest) = (substr($rest, 0, $off), substr($rest, $off + 1));

	$pred =~ s/^\s*//;
	$pred =~ s/\s*$//;

	#print "pred<$pred> rest<$rest> char<$char>\n";
	($pred, $rest, $char);
}
sub pred_exec {
	my ($rest) = @_;
	my $pred;
	my $cut = 0;
	my $res;
	my $sep;

	#print "pred_exec<$rest>\n";

	($pred, $rest, $sep) = pred_first($rest);

	# Leading ! implies inversion.
	if ($pred =~ /^\s*!\s*(.*)$/) {
		#print " invert<$1>\n";
		($cut, $res) = pred_exec($1);
		$res = !$res;

	# Leading / implies a CUT operation.
	} elsif ($pred =~ /^\s*\/\s*(.*)$/) {
		#print " cut<$1>\n";
		($cut, $res) = pred_exec($1);
		$cut = 1;

	# Recurse left for complex expressions.
	} elsif ($pred =~ /^\s*\((.*)\)\s*$/) {
		#print " left<$1>\n";
		($cut, $res) = pred_exec($1);

	# Check for common syntax issues.
	} elsif ($pred eq '') {
		if ($sep eq '&' || $sep eq '|') {
			die "$P: $pred$rest: malformed binary operator\n";
		} else {
			die "$P: $pred$rest: syntax error\n";
		}
		
	# A predicate, execute it.
	} else {
		#print " DO<$pred> sep<$sep>\n";
		$res = pred_do($pred);
	}

	#print " pre-return res<$res> sep<$sep>\n";
	if ($sep eq '') {
		#
		
	# Recurse right for binary operators -- note these are lazy.
	} elsif ($sep eq '&' || $sep eq '|') {
		#print " right<$rest> ? sep<$sep> res<$res>\n";
		if ($rest =~ /^\s*($|\||\&)/) {
			die "$P: $pred$rest: malformed binary operator\n";
		}
		if ($cut == 0 && (($res && $sep eq '&') || (!$res && $sep eq '|'))) {
			#print " right<$rest>\n";
			($cut, $res) = pred_exec($rest);
		}

	} else {
		die "$P: $pred$rest: malformed predicate\n";
	}
	#warn " return cut<$cut> res<$res> sep<$sep>\n";
	return ($cut, $res);
}
sub policy_check_predicate {
	my ($arch, $flavour, $column, $option, $policy) = @_;

	$P = $P0 . ": " . $option;

	# Pull out the arch and flavour from the column name.
	($pred_attr{'arch'}, $pred_attr{'flavour'}) = ($arch, $flavour);

	$pred_attr{'column'} = $column;
	$pred_attr{'option'} = $option;

	$pred_attr{'debug'} = 1 if ($option eq 'CONFIG_VIRT_DRIVERS');

	my ($cut, $res) = pred_exec($policy);
	#print "CUT<$cut> RES<$res>\n";
	return $res;
}

sub policy_check_hash {
        my ($arch, $flavour, $option, $ovalue, $policy) = @_;

	my ($dbg) = 0;
	#$dbg = 1 if ($option eq 'CONFIG_VIRT_DRIVERS');

	# Pull together the policy hash.
	$policy =~ s/:/=>/g;
	my $plcy = eval($policy);

	if ($dbg) {
		warn "$option $arch $flavour $policy\n";
		for my $key (keys %{$plcy}) {
			warn("  element $key $plcy->{$key}\n");
		}
	}

	my $value = '-';

	for my $which ("$arch-$flavour", "$arch-*", "*-$flavour", "$arch", "*") {
		if (defined $plcy->{$which}) {
			$value = $plcy->{$which};
			warn "  match $which $value\n" if ($dbg);
			last;
		}
	}
	return ($ovalue eq $value);
}

sub policy_check {
        my ($arch, $flavour, $column, $option, $policy) = @_;

        if ($policy =~ /^{/) {
		return policy_check_hash($arch, $flavour, $option, $values{$column, $option}, $policy);
        } else {
                return policy_check_predicate($arch, $flavour, $column, $option, $policy);
        }
}

1;
