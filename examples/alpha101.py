# File > Settings... > Editor > Code Style > Hard wrap at > 300
from black import Mode, format_str
from sympy import numbered_symbols

from examples.sympy_define import *
from expr_codegen.expr import ts_sum__to__ts_mean, cs_rank__drop_duplicates, mul_one
# codegen工具类
from expr_codegen.tool import ExprTool

# TODO: 等待简化的表达式。多个表达式一起能简化最终表达式
exprs_src = {
    "alpha_001": (cs_rank(ts_arg_max(signed_power(if_else((RETURNS < 0), ts_std_dev(RETURNS, 20), CLOSE), 2.), 5)) - 0.5),
    "alpha_002": (-1 * ts_corr(cs_rank(ts_delta(log(VOLUME), 2)), cs_rank(((CLOSE - OPEN) / OPEN)), 6)),
    "alpha_003": (-1 * ts_corr(cs_rank(OPEN), cs_rank(VOLUME), 10)),
    "alpha_004": (-1 * ts_rank(cs_rank(LOW), 9)),
    "alpha_005": (cs_rank((OPEN - (ts_sum(VWAP, 10) / 10))) * (-1 * abs(cs_rank((CLOSE - VWAP))))),
    "alpha_006": -1 * ts_corr(OPEN, VOLUME, 10),
    "alpha_007": if_else((ADV20 < VOLUME), ((-1 * ts_rank(abs(ts_delta(CLOSE, 7)), 60)) * sign(ts_delta(CLOSE, 7))), (-1 * 1)),
    "alpha_008": (-1 * cs_rank(((ts_sum(OPEN, 5) * ts_sum(RETURNS, 5)) - ts_delay((ts_sum(OPEN, 5) * ts_sum(RETURNS, 5)), 10)))),
    "alpha_009": if_else((0 < ts_min(ts_delta(CLOSE, 1), 5)), ts_delta(CLOSE, 1), if_else((ts_max(ts_delta(CLOSE, 1), 5) < 0), ts_delta(CLOSE, 1), (-1 * ts_delta(CLOSE, 1)))),
    "alpha_010": cs_rank(if_else((0 < ts_min(ts_delta(CLOSE, 1), 4)), ts_delta(CLOSE, 1), if_else((ts_max(ts_delta(CLOSE, 1), 4) < 0), ts_delta(CLOSE, 1), (-1 * ts_delta(CLOSE, 1))))),
    "alpha_011": ((cs_rank(ts_max((VWAP - CLOSE), 3)) + cs_rank(ts_min((VWAP - CLOSE), 3))) * cs_rank(ts_delta(VOLUME, 3))),
    "alpha_012": (sign(ts_delta(VOLUME, 1)) * (-1 * ts_delta(CLOSE, 1))),
    "alpha_013": (-1 * cs_rank(ts_covariance(cs_rank(CLOSE), cs_rank(VOLUME), 5))),
    "alpha_014": ((-1 * cs_rank(ts_delta(RETURNS, 3))) * ts_corr(OPEN, VOLUME, 10)),
    "alpha_015": (-1 * ts_sum(cs_rank(ts_corr(cs_rank(HIGH), cs_rank(VOLUME), 3)), 3)),
    "alpha_016": (-1 * cs_rank(ts_covariance(cs_rank(HIGH), cs_rank(VOLUME), 5))),
    "alpha_017": (((-1 * cs_rank(ts_rank(CLOSE, 10))) * cs_rank(ts_delta(ts_delta(CLOSE, 1), 1))) * cs_rank(ts_rank((VOLUME / ADV20), 5))),
    "alpha_018": (-1 * cs_rank(((ts_std_dev(abs((CLOSE - OPEN)), 5) + (CLOSE - OPEN)) + ts_corr(CLOSE, OPEN, 10)))),
    "alpha_019": ((-1 * sign(((CLOSE - ts_delay(CLOSE, 7)) + ts_delta(CLOSE, 7)))) * (1 + cs_rank((1 + ts_sum(RETURNS, 250))))),
    "alpha_020": (((-1 * cs_rank((OPEN - ts_delay(HIGH, 1)))) * cs_rank((OPEN - ts_delay(CLOSE, 1)))) * cs_rank((OPEN - ts_delay(LOW, 1)))),
    "alpha_021": if_else((((ts_sum(CLOSE, 8) / 8) + ts_std_dev(CLOSE, 8)) < (ts_sum(CLOSE, 2) / 2)), (-1 * 1), if_else(((ts_sum(CLOSE, 2) / 2) < ((ts_sum(CLOSE, 8) / 8) - ts_std_dev(CLOSE, 8))), 1, if_else(((1 < (VOLUME / ADV20)) | Eq((VOLUME / ADV20), 1)), 1, (-1 * 1)))),
    "alpha_022": (-1 * (ts_delta(ts_corr(HIGH, VOLUME, 5), 5) * cs_rank(ts_std_dev(CLOSE, 20)))),
    "alpha_023": if_else(((ts_sum(HIGH, 20) / 20) < HIGH), (-1 * ts_delta(HIGH, 2)), 0),
    "alpha_024": if_else((((ts_delta((ts_sum(CLOSE, 100) / 100), 100) / ts_delay(CLOSE, 100)) < 0.05) | Eq((ts_delta((ts_sum(CLOSE, 100) / 100), 100) / ts_delay(CLOSE, 100)), 0.05)), (-1 * (CLOSE - ts_min(CLOSE, 100))), (-1 * ts_delta(CLOSE, 3))),
    "alpha_025": cs_rank(((((-1 * RETURNS) * ADV20) * VWAP) * (HIGH - CLOSE))),
    "alpha_026": (-1 * ts_max(ts_corr(ts_rank(VOLUME, 5), ts_rank(HIGH, 5), 5), 3)),
    "alpha_027": if_else((0.5 < cs_rank((ts_sum(ts_corr(cs_rank(VOLUME), cs_rank(VWAP), 6), 2) / 2.0))), (-1 * 1), 1),
    "alpha_028": cs_scale(((ts_corr(ADV20, LOW, 5) + ((HIGH + LOW) / 2)) - CLOSE)),
    # "alpha_029": (min(product(cs_rank(cs_rank(cs_scale(log(ts_sum(ts_min(cs_rank(cs_rank((-1 * cs_rank(ts_delta((CLOSE - 1), 5))))), 2), 1))))), 1), 5) + ts_rank(ts_delay((-1 * RETURNS), 6), 5)),
    "alpha_030": (((1.0 - cs_rank(((sign((CLOSE - ts_delay(CLOSE, 1))) + sign((ts_delay(CLOSE, 1) - ts_delay(CLOSE, 2)))) + sign((ts_delay(CLOSE, 2) - ts_delay(CLOSE, 3)))))) * ts_sum(VOLUME, 5)) / ts_sum(VOLUME, 20)),
    "alpha_031": ((cs_rank(cs_rank(cs_rank(ts_decay_linear((-1 * cs_rank(cs_rank(ts_delta(CLOSE, 10)))), 10)))) + cs_rank((-1 * ts_delta(CLOSE, 3)))) + sign(cs_scale(ts_corr(ADV20, LOW, 12)))),
    "alpha_032": (cs_scale(((ts_sum(CLOSE, 7) / 7) - CLOSE)) + (20 * cs_scale(ts_corr(VWAP, ts_delay(CLOSE, 5), 230)))),
    "alpha_033": cs_rank((-1 * ((1 - (OPEN / CLOSE)) ** 1))),
    "alpha_034": cs_rank(((1 - cs_rank((ts_std_dev(RETURNS, 2) / ts_std_dev(RETURNS, 5)))) + (1 - cs_rank(ts_delta(CLOSE, 1))))),
    "alpha_035": ((ts_rank(VOLUME, 32) * (1 - ts_rank(((CLOSE + HIGH) - LOW), 16))) * (1 - ts_rank(RETURNS, 32))),
    "alpha_036": (((((2.21 * cs_rank(ts_corr((CLOSE - OPEN), ts_delay(VOLUME, 1), 15))) + (0.7 * cs_rank((OPEN - CLOSE)))) + (0.73 * cs_rank(ts_rank(ts_delay((-1 * RETURNS), 6), 5)))) + cs_rank(abs(ts_corr(VWAP, ADV20, 6)))) + (0.6 * cs_rank((((ts_sum(CLOSE, 200) / 200) - OPEN) * (CLOSE - OPEN))))),
    "alpha_037": (cs_rank(ts_corr(ts_delay((OPEN - CLOSE), 1), CLOSE, 200)) + cs_rank((OPEN - CLOSE))),
    "alpha_038": ((-1 * cs_rank(ts_rank(CLOSE, 10))) * cs_rank((CLOSE / OPEN))),
    "alpha_039": ((-1 * cs_rank((ts_delta(CLOSE, 7) * (1 - cs_rank(ts_decay_linear((VOLUME / ADV20), 9)))))) * (1 + cs_rank(ts_sum(RETURNS, 250)))),
    "alpha_040": ((-1 * cs_rank(ts_std_dev(HIGH, 10))) * ts_corr(HIGH, VOLUME, 10)),
    "alpha_041": (((HIGH * LOW) ** 0.5) - VWAP),
    "alpha_042": (cs_rank((VWAP - CLOSE)) / cs_rank((VWAP + CLOSE))),
    "alpha_043": (ts_rank((VOLUME / ADV20), 20) * ts_rank((-1 * ts_delta(CLOSE, 7)), 8)),
    "alpha_044": (-1 * ts_corr(HIGH, cs_rank(VOLUME), 5)),
    "alpha_045": (-1 * ((cs_rank((ts_sum(ts_delay(CLOSE, 5), 20) / 20)) * ts_corr(CLOSE, VOLUME, 2)) * cs_rank(ts_corr(ts_sum(CLOSE, 5), ts_sum(CLOSE, 20), 2)))),
    "alpha_046": if_else((0.25 < (((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10))), (-1 * 1),
                         if_else(((((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10)) < 0), 1, ((-1 * 1) * (CLOSE - ts_delay(CLOSE, 1))))),
    "alpha_047": ((((cs_rank((1 / CLOSE)) * VOLUME) / ADV20) * ((HIGH * cs_rank((HIGH - CLOSE))) / (ts_sum(HIGH, 5) / 5))) - cs_rank((VWAP - ts_delay(VWAP, 5)))),
    "alpha_048": (gp_neutralize(SUBINDUSTRY, ((ts_corr(ts_delta(CLOSE, 1), ts_delta(ts_delay(CLOSE, 1), 1), 250) * ts_delta(CLOSE, 1)) / CLOSE)) / ts_sum(((ts_delta(CLOSE, 1) / ts_delay(CLOSE, 1)) ** 2), 250)),
    "alpha_049": if_else(((((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10)) < (-1 * 0.1)), 1, ((-1 * 1) * (CLOSE - ts_delay(CLOSE, 1)))),
    "alpha_050": (-1 * ts_max(cs_rank(ts_corr(cs_rank(VOLUME), cs_rank(VWAP), 5)), 5)),
    "alpha_051": if_else(((((ts_delay(CLOSE, 20) - ts_delay(CLOSE, 10)) / 10) - ((ts_delay(CLOSE, 10) - CLOSE) / 10)) < (-1 * 0.05)), 1, ((-1 * 1) * (CLOSE - ts_delay(CLOSE, 1)))),
    "alpha_052": ((((-1 * ts_min(LOW, 5)) + ts_delay(ts_min(LOW, 5), 5)) * cs_rank(((ts_sum(RETURNS, 240) - ts_sum(RETURNS, 20)) / 220))) * ts_rank(VOLUME, 5)),
    "alpha_053": (-1 * ts_delta((((CLOSE - LOW) - (HIGH - CLOSE)) / (CLOSE - LOW)), 9)),
    "alpha_054": ((-1 * ((LOW - CLOSE) * (OPEN ** 5))) / ((LOW - HIGH) * (CLOSE ** 5))),
    "alpha_055": (-1 * ts_corr(cs_rank(((CLOSE - ts_min(LOW, 12)) / (ts_max(HIGH, 12) - ts_min(LOW, 12)))), cs_rank(VOLUME), 6)),
    "alpha_056": (0 - (1 * (cs_rank((ts_sum(RETURNS, 10) / ts_sum(ts_sum(RETURNS, 2), 3))) * cs_rank((RETURNS * CAP))))),
    "alpha_057": (0 - (1 * ((CLOSE - VWAP) / ts_decay_linear(cs_rank(ts_arg_max(CLOSE, 30)), 2)))),
    "alpha_058": (-1 * ts_rank(ts_decay_linear(ts_corr(gp_neutralize(SECTOR, VWAP), VOLUME, 3.92795), 7.89291), 5.50322)),
    "alpha_059": (-1 * ts_rank(ts_decay_linear(ts_corr(gp_neutralize(INDUSTRY, ((VWAP * 0.728317) + (VWAP * (1 - 0.728317)))), VOLUME, 4.25197), 16.2289), 8.19648)),
    "alpha_060": (0 - (1 * ((2 * cs_scale(cs_rank(((((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW)) * VOLUME)), 1)) - cs_scale(cs_rank(ts_arg_max(CLOSE, 10)), 1)))),
    "alpha_061": (cs_rank((VWAP - ts_min(VWAP, 16.1219))) < cs_rank(ts_corr(VWAP, ADV180, 17.9282))),
    # TypeError: unsupported operand type(s) for *: 'StrictLessThan' and 'int'
    # AttributeError: 'StrictLessThan' object has no attribute 'diff'
    # "alpha_062": if_else((cs_rank(ts_corr(VWAP, ts_sum(ADV20, 22.4101), 9.91009)) < cs_rank(((cs_rank(OPEN) + cs_rank(OPEN)) < (cs_rank(((HIGH + LOW) / 2)) + cs_rank(HIGH))))), -1, 0),
    "alpha_063": ((cs_rank(ts_decay_linear(ts_delta(gp_neutralize(INDUSTRY, CLOSE), 2.25164), 8.22237)) - cs_rank(ts_decay_linear(ts_corr(((VWAP * 0.318108) + (OPEN * (1 - 0.318108))), ts_sum(ADV180, 37.2467), 13.557), 12.2883))) * -1),
    "alpha_064": if_else((cs_rank(ts_corr(ts_sum(((OPEN * 0.178404) + (LOW * (1 - 0.178404))), 12.7054), ts_sum(ADV120, 12.7054), 16.6208)) < cs_rank(ts_delta(((((HIGH + LOW) / 2) * 0.178404) + (VWAP * (1 - 0.178404))), 3.69741))), -1, 0),
    "alpha_065": if_else((cs_rank(ts_corr(((OPEN * 0.00817205) + (VWAP * (1 - 0.00817205))), ts_sum(ADV60, 8.6911), 6.40374)) < cs_rank((OPEN - ts_min(OPEN, 13.635)))), -1, 0),
    "alpha_066": ((cs_rank(ts_decay_linear(ts_delta(VWAP, 3.51013), 7.23052)) + ts_rank(ts_decay_linear(((((LOW * 0.96633) + (LOW * (1 - 0.96633))) - VWAP) / (OPEN - ((HIGH + LOW) / 2))), 11.4157), 6.72611)) * -1),
    "alpha_067": ((cs_rank((HIGH - ts_min(HIGH, 2.14593))) ** cs_rank(ts_corr(gp_neutralize(SECTOR, VWAP), gp_neutralize(SUBINDUSTRY, ADV20), 6.02936))) * -1),
    "alpha_068": if_else((ts_rank(ts_corr(cs_rank(HIGH), cs_rank(ADV15), 8.91644), 13.9333) < cs_rank(ts_delta(((CLOSE * 0.518371) + (LOW * (1 - 0.518371))), 1.06157))), -1, 0),
    "alpha_069": ((cs_rank(ts_max(ts_delta(gp_neutralize(INDUSTRY, VWAP), 2.72412), 4.79344)) ** ts_rank(ts_corr(((CLOSE * 0.490655) + (VWAP * (1 - 0.490655))), ADV20, 4.92416), 9.0615)) * -1),
    "alpha_070": ((cs_rank(ts_delta(VWAP, 1.29456)) ** ts_rank(ts_corr(gp_neutralize(INDUSTRY, CLOSE), ADV50, 17.8256), 17.9171)) * -1),
    "alpha_071": max(ts_rank(ts_decay_linear(ts_corr(ts_rank(CLOSE, 3.43976), ts_rank(ADV180, 12.0647), 18.0175), 4.20501), 15.6948), ts_rank(ts_decay_linear((cs_rank(((LOW + OPEN) - (VWAP + VWAP))) ** 2), 16.4662), 4.4388)),
    "alpha_072": (cs_rank(ts_decay_linear(ts_corr(((HIGH + LOW) / 2), ADV40, 8.93345), 10.1519)) / cs_rank(ts_decay_linear(ts_corr(ts_rank(VWAP, 3.72469), ts_rank(VOLUME, 18.5188), 6.86671), 2.95011))),
    "alpha_073": (max(cs_rank(ts_decay_linear(ts_delta(VWAP, 4.72775), 2.91864)), ts_rank(ts_decay_linear(((ts_delta(((OPEN * 0.147155) + (LOW * (1 - 0.147155))), 2.03608) / ((OPEN * 0.147155) + (LOW * (1 - 0.147155)))) * -1), 3.33829), 16.7411)) * -1),
    "alpha_074": if_else((cs_rank(ts_corr(CLOSE, ts_sum(ADV30, 37.4843), 15.1365)) < cs_rank(ts_corr(cs_rank(((HIGH * 0.0261661) + (VWAP * (1 - 0.0261661)))), cs_rank(VOLUME), 11.4791))), -1, 0),
    "alpha_075": (cs_rank(ts_corr(VWAP, VOLUME, 4.24304)) < cs_rank(ts_corr(cs_rank(LOW), cs_rank(ADV50), 12.4413))),
    "alpha_076": (max(cs_rank(ts_decay_linear(ts_delta(VWAP, 1.24383), 11.8259)), ts_rank(ts_decay_linear(ts_rank(ts_corr(gp_neutralize(SECTOR, LOW), ADV81, 8.14941), 19.569), 17.1543), 19.383)) * -1),
    "alpha_077": min(cs_rank(ts_decay_linear(((((HIGH + LOW) / 2) + HIGH) - (VWAP + HIGH)), 20.0451)), cs_rank(ts_decay_linear(ts_corr(((HIGH + LOW) / 2), ADV40, 3.1614), 5.64125))),
    "alpha_078": (cs_rank(ts_corr(ts_sum(((LOW * 0.352233) + (VWAP * (1 - 0.352233))), 19.7428), ts_sum(ADV40, 19.7428), 6.83313)) ** cs_rank(ts_corr(cs_rank(VWAP), cs_rank(VOLUME), 5.77492))),
    "alpha_079": (cs_rank(ts_delta(gp_neutralize(SECTOR, ((CLOSE * 0.60733) + (OPEN * (1 - 0.60733)))), 1.23438)) < cs_rank(ts_corr(ts_rank(VWAP, 3.60973), ts_rank(ADV150, 9.18637), 14.6644))),
    "alpha_080": ((cs_rank(sign(ts_delta(gp_neutralize(INDUSTRY, ((OPEN * 0.868128) + (HIGH * (1 - 0.868128)))), 4.04545))) ** ts_rank(ts_corr(HIGH, ADV10, 5.11456), 5.53756)) * -1),
    # "alpha_081":((rank(Log(product(rank((rank(correlation(vwap, sum(adv10, 49.6054), 8.47743))^4)), 14.9655))) < rank(correlation(rank(vwap), rank(volume), 5.07914))) * -1),
    "alpha_082": (min(cs_rank(ts_decay_linear(ts_delta(OPEN, 1.46063), 14.8717)), ts_rank(ts_decay_linear(ts_corr(gp_neutralize(SECTOR, VOLUME), ((OPEN * 0.634196) + (OPEN * (1 - 0.634196))), 17.4842), 6.92131), 13.4283)) * -1),
    "alpha_083": ((cs_rank(ts_delay(((HIGH - LOW) / (ts_sum(CLOSE, 5) / 5)), 2)) * cs_rank(cs_rank(VOLUME))) / (((HIGH - LOW) / (ts_sum(CLOSE, 5) / 5)) / (VWAP - CLOSE))),
    "alpha_084": signed_power(ts_rank((VWAP - ts_max(VWAP, 15.3217)), 20.7127), ts_delta(CLOSE, 4.96796)),
    "alpha_085": (cs_rank(ts_corr(((HIGH * 0.876703) + (CLOSE * (1 - 0.876703))), ADV30, 9.61331)) ** cs_rank(ts_corr(ts_rank(((HIGH + LOW) / 2), 3.70596), ts_rank(VOLUME, 10.1595), 7.11408))),
    "alpha_086": if_else((ts_rank(ts_corr(CLOSE, ts_sum(ADV20, 14.7444), 6.00049), 20.4195) < cs_rank(((OPEN + CLOSE) - (VWAP + OPEN)))), -1, 0),
    "alpha_087": (max(cs_rank(ts_decay_linear(ts_delta(((CLOSE * 0.369701) + (VWAP * (1 - 0.369701))), 1.91233), 2.65461)), ts_rank(ts_decay_linear(abs(ts_corr(gp_neutralize(INDUSTRY, ADV81), CLOSE, 13.4132)), 4.89768), 14.4535)) * -1),
    "alpha_088": min(cs_rank(ts_decay_linear(((cs_rank(OPEN) + cs_rank(LOW)) - (cs_rank(HIGH) + cs_rank(CLOSE))), 8.06882)), ts_rank(ts_decay_linear(ts_corr(ts_rank(CLOSE, 8.44728), ts_rank(ADV60, 20.6966), 8.01266), 6.65053), 2.61957)),
    "alpha_089": (ts_rank(ts_decay_linear(ts_corr(((LOW * 0.967285) + (LOW * (1 - 0.967285))), ADV10, 6.94279), 5.51607), 3.79744) - ts_rank(ts_decay_linear(ts_delta(gp_neutralize(INDUSTRY, VWAP), 3.48158), 10.1466), 15.3012)),
    "alpha_090": ((cs_rank((CLOSE - ts_max(CLOSE, 4.66719))) ** ts_rank(ts_corr(gp_neutralize(SUBINDUSTRY, ADV40), LOW, 5.38375), 3.21856)) * -1),
    "alpha_091": ((ts_rank(ts_decay_linear(ts_decay_linear(ts_corr(gp_neutralize(INDUSTRY, CLOSE), VOLUME, 9.74928), 16.398), 3.83219), 4.8667) - cs_rank(ts_decay_linear(ts_corr(VWAP, ADV30, 4.01303), 2.6809))) * -1),
    "alpha_092": min(ts_rank(ts_decay_linear(((((HIGH + LOW) / 2) + CLOSE) < (LOW + OPEN)), 14.7221), 18.8683), ts_rank(ts_decay_linear(ts_corr(cs_rank(LOW), cs_rank(ADV30), 7.58555), 6.94024), 6.80584)),
    "alpha_094": ((cs_rank((VWAP - ts_min(VWAP, 11.5783))) ** ts_rank(ts_corr(ts_rank(VWAP, 19.6462), ts_rank(ADV60, 4.02992), 18.0926), 2.70756)) * -1),
    "alpha_095": (cs_rank((OPEN - ts_min(OPEN, 12.4105))) < ts_rank((cs_rank(ts_corr(ts_sum(((HIGH + LOW) / 2), 19.1351), ts_sum(ADV40, 19.1351), 12.8742)) ** 5), 11.7584)),
    "alpha_096": (max(ts_rank(ts_decay_linear(ts_corr(cs_rank(VWAP), cs_rank(VOLUME), 3.83878), 4.16783), 8.38151), ts_rank(ts_decay_linear(ts_arg_max(ts_corr(ts_rank(CLOSE, 7.45404), ts_rank(ADV60, 4.13242), 3.65459), 12.6556), 14.0365), 13.4143)) * -1),
    "alpha_097": ((cs_rank(ts_decay_linear(ts_delta(gp_neutralize(INDUSTRY, ((LOW * 0.721001) + (VWAP * (1 - 0.721001)))), 3.3705), 20.4523)) - ts_rank(ts_decay_linear(ts_rank(ts_corr(ts_rank(LOW, 7.87871), ts_rank(ADV60, 17.255), 4.97547), 18.5925), 15.7152), 6.71659)) * -1),
    "alpha_098": (cs_rank(ts_decay_linear(ts_corr(VWAP, ts_sum(ADV5, 26.4719), 4.58418), 7.18088)) - cs_rank(ts_decay_linear(ts_rank(ts_arg_min(ts_corr(cs_rank(OPEN), cs_rank(ADV15), 20.8187), 8.62571), 6.95668), 8.07206))),
    "alpha_099": if_else((cs_rank(ts_corr(ts_sum(((HIGH + LOW) / 2), 19.8975), ts_sum(ADV60, 19.8975), 8.8136)) < cs_rank(ts_corr(LOW, VOLUME, 6.28259))), -1, 0),
    "alpha_100": (0 - (1 * (((1.5 * cs_scale(gp_neutralize(SUBINDUSTRY, gp_neutralize(SUBINDUSTRY, cs_rank(((((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW)) * VOLUME)))))) - cs_scale(gp_neutralize(SUBINDUSTRY, (ts_corr(CLOSE, cs_rank(ADV20), 5) - cs_rank(ts_arg_min(CLOSE, 30)))))) * (VOLUME / ADV20)))),
    "alpha_101": ((CLOSE - OPEN) / ((HIGH - LOW) + 0.001)),
}

# Alpha101中大量ts_sum(x, 10)/10, 转成ts_mean(x, 10)
exprs_src = {k: ts_sum__to__ts_mean(v) for k, v in exprs_src.items()}
# alpha_031中大量cs_rank(cs_rank(x)) 转成cs_rank(x)
exprs_src = {k: cs_rank__drop_duplicates(v) for k, v in exprs_src.items()}
# 1.0*VWAP转VWAP
exprs_src = {k: mul_one(v) for k, v in exprs_src.items()}

# TODO: 一定要正确设定时间列名和资产列名，以及表达式识别类
tool = ExprTool(date='date', asset='asset')

# 子表达式在前，原表式在最后
exprs_dst, syms_dst = tool.merge(**exprs_src)

# 提取公共表达式
exprs_dict = tool.cse(exprs_dst, symbols_repl=numbered_symbols('x_'), symbols_redu=exprs_src.keys())
# 有向无环图流转
exprs_ldl = tool.dag()
# 是否优化
exprs_ldl.optimize(back_opt=True, chain_opt=True)

# 生成代码
is_polars = False
if is_polars:
    from expr_codegen.polars.code import codegen
else:
    from expr_codegen.pandas.code import codegen

output_file = 'output_alpha101.py'
codes = codegen(exprs_ldl, exprs_src, syms_dst)

# TODO: reformat & output
res = format_str(codes, mode=Mode(line_length=500))
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(res)
