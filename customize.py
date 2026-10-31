#!/usr/bin/env python3
"""Personaliza o mecanismo Android derivado de PojavLauncher/Amethyst.

Uso: python3 customize.py /caminho/para/Amethyst-Android
Mantém intacto o código da engine, autenticação Microsoft, runtimes e modloaders.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONF = json.loads((BASE / 'config.json').read_text(encoding='utf-8'))
APP = CONF['app_name'].strip()
PACKAGE = CONF['application_id'].strip()
ACCENT = CONF['accent_color'].strip()
assert re.fullmatch(r'[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*){2,}', PACKAGE), 'application_id inválido'
assert re.fullmatch(r'#[0-9A-Fa-f]{6}', ACCENT), 'Cor inválida'
assert len(APP) <= 32 and APP, 'Nome do app deve ter de 1 a 32 caracteres'
SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
RES = SRC / 'app_pojavlauncher' / 'src' / 'main' / 'res'
GRADLE = SRC / 'app_pojavlauncher' / 'build.gradle'
if not GRADLE.is_file() or not RES.is_dir():
    raise SystemExit(f'Erro: não achei os arquivos Android do Amethyst em {SRC}')


def rewrite(path: Path, func):
    before = path.read_text(encoding='utf-8')
    after = func(before)
    if after == before:
        raise RuntimeError(f'Nada mudou em {path}. A versão da base pode ter mudado.')
    path.write_text(after, encoding='utf-8')


def edit_gradle(s):
    assert 'applicationId "org.angelauramc.amethyst"' in s
    assert '"Amethyst (Debug)"' in s and '"Amethyst"' in s
    # Não mexer no namespace original dos pacotes Java (net.kdt.pojavlaunch).
    s = s.replace('org.angelauramc.amethyst', PACKAGE)
    s = s.replace('"Amethyst (Debug)"', '"' + APP + ' (Debug)"')
    s = s.replace('"Amethyst"', '"' + APP + '"')
    s = s.replace('"amethyst-legacy-"', '"memk-java-"')
    return s


rewrite(GRADLE, edit_gradle)
rewrite(SRC / 'settings.gradle', lambda s: re.sub(r"rootProject\.name\s*=\s*'Amethyst'", "rootProject.name='" + CONF['project_title'] + "'", s))


def edit_strings(s):
    if 'name="app_name"' in s:
        s = re.sub(r'(<string name="app_name"[^>]*>).*?(</string>)', lambda m: m.group(1) + APP + m.group(2), s, count=1)
    s = s.replace('Amethyst has unexpectedly crashed', APP + ' fechou inesperadamente')
    s = s.replace('O Amethyst parou de funcionar inesperadamente', 'O ' + APP + ' parou de funcionar inesperadamente')
    return s


rewrite(RES / 'values' / 'strings.xml', edit_strings)
rewrite(RES / 'values-pt-rBR' / 'strings.xml', edit_strings)


def edit_colors(s):
    for name, newcolor in {
        'minebutton_color': ACCENT,
        'background_app': '#0F171B',
        'background_overlay': '#293C40',
        'background_status_bar': '#0C1115',
        'background_bottom_bar': '#172329',
    }.items():
        regex = rf'(<color name="{name}">).*?(</color>)'
        s, n = re.subn(regex, lambda m: m.group(1) + newcolor + m.group(2), s, count=1)
        if n != 1:
            raise ValueError(f'Cor esperada ausente: {name}')
    return s


rewrite(RES / 'values' / 'colors.xml', edit_colors)

# Cabeçalho novo sem substituir IDs nem eventos da interface original.
banner = '''
            <!-- Identidade visual Memk; controles originais continuam funcionais -->
            <LinearLayout
                android:id="@+id/memk_header"
                android:layout_width="0dp"
                android:layout_height="wrap_content"
                android:layout_margin="10dp"
                android:padding="16dp"
                android:orientation="vertical"
                android:background="@drawable/memk_banner"
                app:layout_constraintTop_toTopOf="parent"
                app:layout_constraintStart_toStartOf="parent"
                app:layout_constraintEnd_toEndOf="parent">
                <TextView
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:text="@string/memk_header_title"
                    android:textColor="@android:color/white"
                    android:textStyle="bold"
                    android:textSize="21sp" />
                <TextView
                    android:layout_width="match_parent"
                    android:layout_height="wrap_content"
                    android:layout_marginTop="4dp"
                    android:text="@string/memk_header_subtitle"
                    android:textColor="#B9D7D0"
                    android:textSize="12sp" />
            </LinearLayout>
'''


def retarget(s, view_id):
    pat = re.compile(r'(<(?:[\w.]+|View)\b[^>]*?android:id="@\+id/' + re.escape(view_id) + r'"[^>]*?)/>', re.S)
    m = pat.search(s)
    if not m:
        raise RuntimeError(f'Elemento {view_id} não encontrado no XML da tela')
    old = m.group(0)
    new = old.replace('app:layout_constraintTop_toTopOf="parent"', 'app:layout_constraintTop_toBottomOf="@id/memk_header"')
    if view_id != 'social_divider' and new == old:
        raise RuntimeError(f'Não achei a restrição de topo em {view_id}')
    return s[:m.start()] + new + s[m.end():]


def edit_launcher(s):
    if 'memk_header' in s:
        raise RuntimeError('A identidade já foi aplicada a este layout')
    anchor = '<com.kdt.mcgui.LauncherMenuButton'
    assert s.count(anchor) >= 2
    s = s.replace(anchor, banner + '\n            ' + anchor, 1)
    s = retarget(s, 'news_button')
    s = retarget(s, 'discord_button')
    s = retarget(s, 'social_divider')
    return s


for variant in ('layout', 'layout-land'):
    rewrite(RES / variant / 'fragment_launcher.xml', edit_launcher)

(RES / 'drawable' / 'memk_banner.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
  <gradient android:startColor="#143337" android:endColor="#102024" android:angle="0"/>
  <corners android:radius="14dp"/>
  <stroke android:width="1dp" android:color="''' + ACCENT + '''"/>
</shape>
''', encoding='utf-8')

(RES / 'values' / 'memk_strings.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="memk_header_title">MEMK JAVA</string>
  <string name="memk_header_subtitle">Minecraft Java no Android • Base Pojav/Amethyst</string>
</resources>
''', encoding='utf-8')
(RES / 'values-pt-rBR' / 'memk_strings.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<resources>
  <string name="memk_header_title">MEMK JAVA</string>
  <string name="memk_header_subtitle">Java Edition no celular • Controles, mods e versões</string>
</resources>
''', encoding='utf-8')

icon_vector = '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#173C3B" android:pathData="M19,19 L89,19 L89,89 L19,89 Z"/>
    <path android:fillColor="''' + ACCENT + '''" android:pathData="M27,77 L27,31 L37,31 L54,50 L71,31 L81,31 L81,77 L69,77 L69,50 L54,66 L39,50 L39,77 Z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M27,25 L81,25 L81,29 L27,29 Z"/>
</vector>
'''
(RES / 'drawable' / 'memk_launcher_foreground.xml').write_text(icon_vector, encoding='utf-8')
for name in ('ic_launcher.xml', 'ic_launcher_round.xml'):
    path = RES / 'mipmap-anydpi-v26' / name
    path.write_text('''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
  <background android:drawable="@color/background_app" />
  <foreground android:drawable="@drawable/memk_launcher_foreground" />
</adaptive-icon>
''', encoding='utf-8')
# Ícones incluídos no script para permitir upload apenas de customize.py pelo celular.
# Pode compilar mesmo quando a pasta assets não foi enviada ao GitHub.
import base64
ICONES_INTERNOS = {
    'mipmap-hdpi/ic_launcher.webp': (
        'Qb|Tess{i7S4BclR!}%t3IG5A5C8xGM*sjv002QuP)HmB0004iTU&eE=7T^d4xk)20JTWkg0(aWwF)&4)j4N(!2kb_3dCRgM1+EX'
        'X&VB&3aAA9##jL9$hoXGoExP8tigUP(9O&0jfiW5=&dUAE?^I&Q@ltNUW(3MCs<yK_&{8*n1UC%ULx6(wTNel0(+75A17EzAc+PA'
        'S^cubY|m@7#~Cadrujf5Q6YM0nnr?+c!`Xc4HC3Im}86iqXp#gcM&f+u;mb6fw#Ea3C9=9?sD>>Lm!i=C}Enh4srH>xb*Z9J^e^e'
        'UsKZ`74=y?{aR1o*E4@mGY?TSpHVa~`s3xbh!0fr7gO*e*ULQtEIP%DMB%0Azyf=XZeCVzL|hw0Z&jIhaUg)P0Me0jS#3BsN&#4d'
        'UjkN8I3Q>S002-U0G$CUNB~FxJ{byxL7@cBXLAGqVJyHG-$Dyx%D=gB>+Oev|8BC*xvTsy+y}s~@E*WE%Kc5cb$NjPG5oLnC-'
        '@I|Pv@WKf3SP4{7Lm1>vHq}{YL-)>zDe+@O%3y`xWf{cwP2BRR2;xZgTa#U-'
        '5_J&dJ~Fzm4CR9EABx{CDLCa0fBB`7g?@aGC&qUH?Vs!~Q?^|H<EO|Cs-'
        'P|9Aca_XFq``A74w^dFm_;eJg0YX02&9saZjTl{2OZV~BxPaqZqUQQxuX*A?864t*5=<)ndIBphI^4)yh@{B6CNDCT6nO+5Ly%xb'
        'uZ`a7QGs&?NbU_^Sh`?Cm{Rbg)?4dy5d(|GtLO&`uM{*5b_y!KxEguMoy#TI&0092~{-'
        'h?5i{BwcBC)RiRzA0pBe0&@^8&{P_fEptUT6comcuGvE;-'
        'K0ffCG)ITN2INy4X9AoOvpgJNzkC!ztkglAKKP}`o?jp_{(jFsLO$e%m+aFZ`sm=)A@_LNF(O^6;NQf3_XyOEj{7f*<P?jDS!Ead'
        '1K4IEz=<%EB5@M2h21xGcC!akfOS#fj`%D5_C6Q?VN2(BG1cl6$;=xl<^d3$Boc~wwF=u^8xcGx;$onU(d5HULZ%b5zN<50f`n(-'
        'gvGw-l;0ec$iG;XWA9I3P2KI7~)h3u3XQ-'
        '&pA<)!H!49*B{fVBUgJ@G0&W8rlAicE%=NCnpVe?UgJfKk<h^)5H!68nFVe}L@9Cdykdg#XhSzV9fD_LiqLz^H!&t44G%p08FBJV'
        'lo~q2LiMazG*S{(ELGldfM|bM5m3m^?i8MD5LIj?Ylup7XZzXFA|}IvB29@VE9{Z(kY%>N5iUXH4jpMWu%`wy+0A(-'
        '<WAI2r6`cg~(#a6W^~A+O+IbtUD@%(gv`_~;p1&?+v9JX3E^a3EV!w*a9NE*yqdy%v*K!Fs@=!x%Wa2!G$oBf8_+-'
        'yl}G*aHJgC?@`QHh2Zu%s=nnl)NVmAzF)Lww6W5jT66aDNEeoKz<2M{oB!0#K&>K1-'
        'r3apfxOr@bga=M1jhD`D*36*W?}zy{dXZhbiP@(}FvAM>tC>Cf(j%w)-'
        '8EHwPdOPvj;__D>YZJs9OQqj4rf&Fc7O_7>8j_)MYGFTjS0W1+nTH&OA2FVmZb#9LQ(VmYr(<)MJ{boXE~>sc@Bs~)>r2Q8p*F{;'
        '%Ad&;fm6P&hxHRZQo@R#Y`*<cl<Dev+pY#H<xhKP{Ke0%VEoHp`ZQjHpZZT?O7v|n@0tgaJPG=yVsbT=3%%+(qQ!LqdIQ{(ibOM1'
        'AVqS3W(uI5wv|LTnJr70p7Z+~EktykK&n?9#%&psv`PK~(wt&QJp_pX3%p3cHN=*ZRpKl$$f8s1~PCV3MKDd@~JWjYos^J4nKe+#'
        '4D{#B^c(5jSfTD&wh>4PAvD76@5D1$$O1)4Xpil1Qf#U^&1e;V>N|Nn3Po`{tW)ZQC1ZtxLyW$?jMbE`0v;46U+Jb@Rzo;|xegu>'
        '7o&!<FtAcLqff2v{6-'
        '~N%2ajPnPE5nF~qgP+Vq&L!V6Y)fG7#=Jn+wwf@1ZXUqPT^zloB6DF#Rs_Z4&0u=#%Z?BhrZ8<QNI!^znr1J<bCk4Ic`EVjIS*0('
        '8pR7&$Sz`d~>dN?2i$tt9_T*tO|IF_H%_i(Ov-3zxvPy`r<B?1-'
        'CL&Do7<_GQY|ys9*@4&`mb99QbjhXX`&q(+CsW=Y#wyYHRM?|B?&Qa=O=)c+vp<w|)!)!*~$@vTQXk=`A$KkC}B{%utA_hlVB#q+'
        '1O|*vA*rzG4n+c``o&E>Ullff?|mWyP@C3-'
        'O4VEJbE?Mh7@_p5L;}z@P8gxojV9?aSC(?ais1g|QVVG=E9<IwX?A4g8TLoN=?V*)Y?j;h=UaWc3&fG@iKzU15iwGSEjR?jM>7Ui'
        'o<vAAgOxNsTMMixie|Z2ow@w*AR4ZGY4#4o>L*UUO+oGhO_^Ho8E^>iAje3h`psMjvGz!;B;jSp+G<Eq?={e$!x1)F9z-'
        'c$gL}RY0JO=UwJNVy4;`N``vRqQ>t9?$H-'
        ')G)G`v@T~wbNO3E@NM?Nc^<m&1#!0$sh`&51+ujtx0Wi5*PzWOL&UBlKR683Pc^E4|000'
    ),
    'mipmap-hdpi/ic_launcher_round.webp': (
        'Qb|Ted<y^oS4BclR!}%t3IG5A5C8xGM*sjv002QuP)G&?0004?blci7NxJX*ylvaIBeHGVw%vcg#?ZEH+qTVFvF(lrw-'
        'K57#rL*`5itR1Iu*fRXI!e=>2^EaWoJnMkV{6ZvjCWGjl*wxZTxTU5$^is+qWOT;Vb|ow<l*{#=UME%Lc!B;IKJ?B<)B7EO+)elA'
        '-1i!-'
        'ShU$#1S)1CZPT0am)*NV8yrVMg+?jes(!lriUpMryF}upn<<6e$lxfc?jj#sQo2$0IXj00lGLKq^~k<m2<BG*+;}N7P^|Lpgpkl!'
        'gj6|B1@h8hIc}YNB8t(%52m9*5FE!9H|nt3!Dl%BTdJ(St1y<)J8}$msm+&en%=OUQ^)p6*i`D|G*M0pyVgZl<zI<4coB8cwhem6'
        'a+_fee%LEML0U5~fQh=_k0D%4&^|p`W0u7WL4$HA=s`sjMm9E;#{$CCyp2aZ?na;2dgQ8uvqxFx{7ox){1Bq+kykD_5R?Nd$L<)@'
        'FPY3DZnq)W+y71gt@4^~ODcBdGN$F9B|*)#rQ}=?!{)!ErOpIDt_g>B}wM<KJQo4e@WH+l~J_hW<8|wZDs5zGVD8<ag=y1;3mHch'
        'c%}z7Cu~txtIkumSz=;2>beZyD8vFNKVUXtg;%lr#wrtxtIxO2(`|Fe;1aLLj(?T9?IhDFcF)>6LL86aYCrL#xT-iz!k9AXv99<^'
        'Cx6tKfEOJ;v81r#?9?_>)C7$~7VAFF2f9i}Df(hE0;6qSfL2bXrNnA*Xr146h-'
        'qw*oRoD%hAB74&!z1S2mvkQ%M)@l+Iyw%|Bww5-QVP|~PSa2(Cs6v|5=38PO1hmzJF51s-'
        '^XtZGKuc^@z<!^^T5*jX8<T=vX;LZ<MMM3j|Nlxz3d{A!WMbo2TkQo?yfOLxin2|582M7k61lZwKlIqcjE6I-'
        'zN|1zs=Zw6?JxbElV<h3KB>Cj-Qv!lk3V<a~cvactd#9}cK+syr02bNf;upuLdqjl0Pk8m}gO<%el7u$rg1^qNOsCWB+nEJ_ErO;'
        '2R!}$~PzV43kSPG20V+rUNB}+=3WPzS1ol^y1OQ<zMfcD%cb4=4`iK4>gaA#HOvqK&KO8?CzD=vo-hS?W>~w0KuF(G7_UG^u{a5o'
        'pd0%KAjNMZFz<(S5YyQ*P1NukoN4c*+577<)f7d_%{<<IUKgoO>e%b!qdn#rQ_RIZi@&oo)xKGTUo&MTp1bV0BM<Tx9@=5(e@$2^'
        '+(O0+|mVYt-EBOuM0r<_#J^n}X$KCEQ59Hs~Kg9l7|C0DI{|Ebb<p;LE%s;39p#JyyA@&RWYx$q}|Ly;|f8sy?{VMv^{ciR!{XqY'
        '|B{`sWw2%!Lk<dtvr<_M<egLU_z}mcaCLj6HfASfYTTM=QO*gLO71t>P2~-(pdl;a(1RNfF7o032Y@%4D4kiC5ivUP-'
        'V$1C67BJzsKwIe7YyYSFFN3=KpZ=Js1XH#=Wz4zwaww$<fB^pg?nXB|oqw6o2eSPh8V=s+64-'
        '^l5KzJ4Df>~x@n!G!SbjkS>6%;5=l%hIyC*o~=V!w*XC)bT!=_-?anDa^dSaxDzZKIgbQYl4(8+n-'
        '!t|tEf{?@Y1W!*QZsQw+q;lkVI#@N7fN8F1vPXDV@GcBM|M}aG(~ryavT|sgVfx&*LoM-uVfs4mT9Jn%Kd7*2&H;*D6bFcZut-'
        'z1E;U);BDv5pTFX~aGbD_sVWo8kQD<kSI~Z7LvV+oksNZ!nY#z=231B+6D^y3h*6HtKL53?o_h<UW`L=hGJ8swb{<M1Akl*GoewP'
        'HD!C;sjstMIbCDj4ayV|_#S_uPiPml3<w+{>WFwmEl`+qol{BUzy#9WqjO!1Tv*(NSW8H<SmmEE(paq1Ezy|b-Y+Wn*bB?t+ye-w'
        'JOgujZqRQ9*BOeB24S1SK??vO7jz=qn`0IfP+)lY(GtmS3{7Jl_0O)2_6S1m8Q0a;!wr&Vd*6)MXM8QK_5zbf+y><qvE{%+dvor!'
        'tOhS%G_i7r4*j6aE+yR#xB%oqQz9I_6ueW$gRHrjXFxf=>M>hTqD1Qy?%P@N8*eByiQlC2+DsVP;r(4A(gpT95X;1^679N;#F`cJ'
        'q2UwZ&1$c>^=n|p{Y?WECuU||!6uG>#BC2pHJyMxDQ(6oea<=K?Nf0$=PItV7zw<Q0KRwhnNlE-Pa;>G;yLHKbFq##+2uN6;EQVW'
        'P*pim1E-~#NhWAu}%lFLVL{-*ZkS4qsqdo4UodvcgTYwz(R39}D~@EIY`CACxZ_^+JP>WQn~FGvcyw6mixiVDGUvt(S95-'
        'X$SJ}L~p60Gj|j=Al$*$UVvTi}{0t0*z4`(ePhQ+`{ZrvhKIi#ZhzQh4(MC~b5O6uHO7Lr8E2#6#dlm4KYa7ek)(Rd;ygyM>p~A`'
        'e!EL6^|%n%4nRtCs-~%}DzcS2Ih4hg;9LOMr>|7_FY$MH8;Wl_~D-$%pf-'
        '0r<}G2k$qrp@_3VjIvPd{``iN+Ph(Huyy1llxZLpoV;C9GZL6yHKh+3&)Y|*Nd@)V?=?kBSxi1&<&fAI8=R)+c@QOBYxI-nIrxEN'
        'Unqm;`*L!Fn<2gV_!0J?xnf!N%gRgTH;kTdr_?T-Uh3yT?a-i$VQVP7PJa0({JG_|BWdsG<;7-'
        '^II$?;h(Cr@_Z9w4+}FI%UhUb!Dc?ct=@iWl(UR;CGo|%JFs%m)yAXE&f3%eP#a~xjtbabPEn~KIC})qWWQ&ke-umZ>Q?<iiN(q8'
        't<1^7Bi&-lwQzD<7qkDR;2jRvL<xgI#G3E%=(U7kzI<MDlYD(SF_6B0f{1o~~P@G#dV9720$x5F{)mI-'
        'h2+Uh^VYeG9hYu|P8r?%92Y)1qT5nwZ-bLg!2*3KTlJh01WgR4?b^p-~HUb&4r?lCQEK^?ae#XdLfBiQA6l8?#4N8r=?1-'
        ')UTGhZ<{SO|n|J^=n<S2=s_(JP9%*fO)n@n}z?Ta029Us_^|1gQRhj(}}+eCq+Dpw&0VtUL{o>7;eYT6U}P`py_>}A)*4!Z08lNX'
        'd53vQ?Lh8_E4a_9T@Q5bpz^1pdE>0|bQYlCCEHb1z5aR=-'
        '+cFHjc#+e>}d;HN$Blj=nF(<{Bw8_1Wcc!gQ)xa3JC`Yr}<*7^WitNV1(wROD-'
        '*R;+|HIu6r(ywJf4>qUX!HyRd_d`6ZLjQ5y<E9ZB5-'
        'gYIZORY@!8#g8UG=0UUYB3yKi!#WHXARC;vEGTNl~oSRJUK&^O3dqbxiZg%F<9`$iig(%A%|-fMt%qRpCafV5LLnEx%ab7Xmw-'
        '>86iI@z2+WAJn8^(*!0XsL2(8S2%sThzz;Ho6vQwcK8+*|sabx8XeKIHlptY}V9jcZxVPQwZe!JX`u1+Xj#2?NX|xGE_2u^iZ%%I'
        '>sn6ZB(KU%bdnG89f3$dB4|;Tt?DXVn>u<TQfw{*=s<o8c1~thL$Vv2)a)OeQ7ornf$yhLao-'
        'Gr~mZYfB*Q#h5!9@ANj}q|DFH#?;^jN97zf*n8UyRX{*wi--EVYi|-'
        '=&@Lie%NOY%WBh=%|`aqR3(FBn5oMJv3jqlA8!q3QV0pu@Y4lR1C$#lwRmLdq%61M_<2<2l9{))MPLW4?7^gp>#Q8P)69uMwq-'
        '@WLWUF|S2m`nsHo)9Q?1XaGH#6aURn5Vf_W36`0C0@Kzl!k)&4G>VcZgLg3kS9qiFKc!ev*J*Beq_Xb$0ynA!EBspTkG{?68Qqcr'
        'eX5e_}6mIjEmI(NDbWU1U<^4l^^|vxG7;fHg~bW_F?iMEa6xG@_!%z00000'
    ),
    'mipmap-mdpi/ic_launcher.webp': (
        'Qb|Te3IzZFS4BclR!}%t3IG5A5C8xGF8}~9002QuP)M8r0004S8%dJe>_03Z4-'
        '{gduvH#V`Jfnt%u18@ztm#s(ufEHY1_2i!aEHBoCk_g*);9PHcdGy0PleN0mJ!*U%QzP0rzlOM>5!#29jL{2j|lj&ldT$(av0@-'
        'X)mvNRda*kf6sCWuDjr*3ooWTqEC8>OP+`C<&a_G$qEmRnz_-qW|;yj_5n3@1VZ3`i|>&f_#VkVCTqp6aZFGI3P#_001x;0G$CUF'
        'aR(BJ{bsuL7@h!Rs;ZHEdUdyUd)^LOZcnRgSU^wbcYass{TvL0qQCJS9AyKckBlU2kh@zpP&cn&!ms)ufbpI-'
        '|ff1H|p>Hno*yTypb8f_K(PZO?BM-j^R_`pRvD@TEIVKzZ&__V~_kl+Xu-H`CeasiT{`RZ}biPXZjELf6Nc-'
        'U;q3ve#v_feyW&#+3>(ja+PiT52r5Jmlf|GZ@!|IC!$cZ1z|QRiX@ba<#7;Kiz4rK?_Y8L{aBcQ0RI2};EY&<90^mr9$y)f9x>zY'
        'IY_>u5%}Hy(ZG4nKAyHH*;TswSMQPB^5#xl>X39XQ6|<Lk$C8vdM-KogBwOPZ{ce{%>U`V4g1nV&|V~meA$El_^z~lxEp5Hn*R@c'
        'ZZ3G7OVW+Dx9Kr#|7(=hPkj>lW_op>{}y7eQ8qCFO`p%hNw}5*lJ>WR^*V>HrKMG0j#)qVPZ+U8Qa6nLB=0^4_n%`|{s)rpnRkMK'
        'Hy4lg*qQhP%{V}I8+tNWlQg%-asSKa`bfzU)^=yiD%szx-OfIe`R&x98qL+I2Wb27K9gVY{1qH~<YX^f28|!JMC6GW^8&pB8(|PW'
        'sb_a}$$Y59d{`p%uubCYI<Nnj#+dBb>jx)dknAL+4!=p{e4F#hP8>%>I(81Y7o~Sc*Oa88#r{v?0E9Wa1S@3&mRF1RcgAP^(yxcD'
        '0HC`&=LsCmj<dc$oz2FzMGu9?5OOO0eq{qxM!Z3rYOP_JE-SfpcM`%Wk6Tsu<q~!ZxPk4V&^ox2XxfOR%v7s+n8k<U)p}Jh(0$wO'
        '$Q*VT%qsuQy@!HAykxvp4hc2GKQ{7tQ2YZTU1x;;tf{a2PLIllr*X3$+x8R%bCY1AKLJuj9;0#9>W4sB{&9(qDE>Ws@GXGSL;t^('
        's)uRd4t{?gh=0uw9;t5e7Rp_M1!{muO~sIzTg|7-1N_9<fMk?h|NN+%jP*fwbI)>*`wno={?sj-'
        '1+@%<#5N<w%N8Vfm71=@8~y;us4Li?{~y2*36(GkgLLU+-L5iA-gJ(o>-'
        'o!A(ic?gRQ|^J`79E*v6$N5lR&|>j4O&qOADm@UT1vgwRT?*e=Cpc3_pMQnAuIFMWAVT3^sqf+4WM`jxcyFd@97YRe;SN2Y=U5dp'
        'hjS#QIp!+0Z9{eYogy2iCou_}tZok;BV|{l#DV!wZ)x+)$|N=E{(aj<rK6OmY--w8Z-'
        'sYq#FObinoq)65MQPXUV7H^c76;z##R4~_S|-;BSB9fKNvJTJkoYrAA08-'
        'wo+5nqHBzXMF;v*B+r|NL_E34Evk{O<0WxIfE<Hq~pK?zXU2&4uKTYT?8aeb|;jS^df9a9B01KjI^oMnS`S5LJh7N;6OiZ8_(3Js'
        'EJlsRB5@cZ6?Ch)U{YJtZZU_db8_Jypku000'
    ),
    'mipmap-mdpi/ic_launcher_round.webp': (
        'Qb|TeXa@iQS4BclR!}%t3IG5A5C8xGF8}~9002QuP)H2|0004?v~8PVyI#>-'
        'RUO;5ZI5g_LtC@8_Kv5vt&yF%hfYSe?XIrxO>!1`)pa6b0+6{50H9v~S&2j<F?Vny10c|dT^XS0;7!-'
        'QG3}4rJ4clQjEczsHJ3dgNr_SlNj_iR5HPU>D7N?`>8ul`6=x&z`^vH~*(r_QcS-'
        'A*wOI1eNGO$sQdmS<VXR`wRSG&IrGou*j<LIlr;9^ppmcD8p)i*rFBDfQjS6spA#)t^ya`mQ01Fv1=OH&BNMX>OR&vLXqhSCjUGy'
        'FuJ#_AEd94A1#kBO&atjQ!s`}N5AL49NWdbatrKgtL5vU?h#rY!gxjZnC5xtE#5!fQuBRL9llg=OE)8h4h&}-'
        '>5fZ~(mq&bXyikP40TQd2-m*-nzzHj-'
        '1DLy$)YxIj=OSb}d>HHDCEQMWS{fXo>FoKakmNS78uf_Qy^1UhotfckD@*s>>b$&VVB$9S8Fjz_Jhvgv{K<Uyi#Q7lZOLe6I7z}0'
        'TL&zyG_-}yK409LqAOfURfj-MHS0S$!F)9_5Dt3WkZbIIy2#xd_#m~~Z_{8#ZC1_--q1Tf(E=%q&0*%a-'
        '!uS`YmFy%EewYquWUCA+Z?a?*NhT6mlKX4JD8y)hR$Jebq>EBIlKi@_Ghh&}GC-'
        'w?haU;kKRY$E24FN|*8zYMohBp_$z&oirCS*Q#vpS5R!}$~Gz9<vP#XZ90V*&6FaSOo3WPx+1yxl90AVeF6Q)p)Yxxf{D&zMLyqj'
        '^Q2dpp0eY$qM@eTf?)sxHz=!g2R^FH#vfIk_%z&~3$!@U4MTfHp*;s1d6GX0(Q2K{Ndwe+joW97eCKWy^={j-'
        'I=tN+ISKyYGk|K#7?KPmM?Kf(T4``y6v{Acuk*pKiZ4&TgvReJ{cxBU<HKY(xJzsi5aeqR4~|Nr5S_5;|D^<Y<2x=rUl6}Xw!MPM'
        '%4GgtC`O%*48y$2g&NtBPpbIcO!)&{VdGzXhmuuQdD|1o%Odq_Y4{_RMA@InH=_+G{PN_E|UuW6R=YIXZ%U5owGEl}qL{)P9-'
        '(DoN?Z~r61zCmtl;cBJ0#)TUH()aieVRp=@upU6Gs3?eyi#MOI2jIMcg7yd!tm3V+Q|GwC`~Y9Vr(qE8_9ER#FaO0!$7)d9`Uis5'
        '2(ZYJT<a|uOJ`KMI<A9B$Vj$QqZ6MT*D3X`{~4eEF-'
        '}Y(Nf(_jk_WT>j$x90n&%xc{=G*Qi(vmyZ<72uFZ}S7{GVv9+1Nr8Q_L3zg-'
        'm>a+YCTO3UH0+R&ps^6{`PATmR<|ly)^;cKJrRBt6w)i;1D7bw9bnErl4;lFcbMMgOXB4bo;o_C57ZMfx4gG7G@Xf%M&qYIXMuuk'
        'Fp_T)>V$s$t2v>W?NZX|nQ_O+^;5Q|~@iTEuu_+{dK)eE4iBT%mm?-'
        '@^cTfBk7wi@ONRE)~?PTaNofg^2PU8oub=mr&9+8&$!JKbJ4qnSwlT6czp}b?1swM$!u;bNz=TdDn?4ML`g~{5-'
        'M`>mYrSs9)r8B`)4r!oAw}0Rxk~`)TCmR`!6G(x8T}ZkS+xma-;Bhe8-'
        'I6Z<s^luohZ=X?YZTL*90tkeRsC#*8UU0=qKQ<)BF?dC(8j_~GoDz$JFMOrDO6lUNobTe9ev4mMaWBfA^sfl(eXw8`zuRea0-'
        'rC1!O8dJj^?*?Kf}UzMyqd`0-'
        'syr55;jA|)geZgz(pSKeGVYFuYI7D@L6}JPc!bc;v#{;L>jicXFkl3z_(nUlZYGOtj~PijWqV~`9gFf0h5LV-Tb5J)3SVHQJa~Pd'
        'BADLfugoX^ArYq_@}wbpN1n4iWAKjt;|908MfinX%G^cDgPi7a-gN<0X2hs$h!aT9%H+*tXy5Pcg7<kYex<DL@)%-'
        'fjhe%HB3iYMz^=JcmZ)=riycZ02SB%cWd{tHDSoOBS*=fy2xi-Myw0z-5j5J-'
        '^D&5T_M?c&1>(`)o&K(*&Bt(k3{E%Z+|OhPM}IS3~<0q%#U%0F+Jnr)Ncik#@$yu{5jIe`6y1uEQ@pEA^-'
        'S{pJAV7Q~!)2H*CcSi-M541v%*eQj-nVD)BUo94bsj9t!Kwa-'
        'ays8|mD_7F&xDZ!MSWA^R1`YqOaxYjYV1eDt|}8Kqbgf3?|NEM+jJg-iwdWK`R-'
        'NWio8Y&&my=m2J`FpM=|;mgb;JQ0Kbc4@H)6+=0LxNCU&V=o|cRVRDt{Nv-|EB)p};|E=H-@}NmX(I&O{`T6CJr;R7Y>Z!c_t-Ay'
        '4m9x_;mO-b*E6-fVU_p%8!s5Gg##WVD5L*Oi2<M-H0gM+-'
        '6%ba=q`Z{XF`9Qhwv5kpl2RXa}$fZ;uqRD1k|f?I2aVwKHYCa)!x6>$RlG~9&vt3{!RtX`#n;>OyLu8AzK*my7(QCSH_Crxsc+~6'
        '>ZfrlDvE5cAkd%^LfpyuOI*b'
    ),
    'mipmap-xhdpi/ic_launcher.webp': (
        'Qb|TeUI_pIS4BclR!}%t3IG5A5C8xGUjP7K002QuP)M2q0004yTidqVMhEYMxlHD204tFrDXAzf_92&%RmenGjJQ|;VvYR||BjV?'
        ';h2b+0G?VUBScFTFPnh<^Xb)H`;PCfrsw-WdWp(Nqxqu(e4LLGRz1sL^dQNz_wU-XOL`cAJtMJwA-NX?Slp$HZPJr!hAVlmFniZ('
        'Nd1IF(<v*|tga#b#%MaZf^~Hb_6xI(wOrx4)*EI&C9ahfaMm>mNE|3D<g5b{*q|*Qlb3d2)EvnbwCjl4Sd<)9E(?sEk1A0WecXXF'
        'xx#jx!K~!Ca+$%6BGV1rs*kJJEi7YOLK|EA-'
        '+zBZS;n@6+t_a5Mmesm8<>^I$_&orak<W5=c7tgMIU!C79~fO%L1!8l1Jq_qQ(Yo@tC}{1B1kYa!gqVBp`9E98uOa3BYV)Esw{w-'
        'Z1+Kqv_<)xVi@8*NLW6jwP#WNc_HLxRUpA^sd#Anx`hVFC_O8L2;KZwn;qQVDuo#v-'
        'j`XvrBpyf$`kRNTd0q0(_j05?1ko3D`fMUfs3t`0i?Yz7Hf`wn|2bmMWeKR!}$~o(BK`5Geqi0V-'
        'esU;sWD3WPzS1y<F71OQ<yz!>d7E4R$gsD3khLt6i=eaYpxGkj3|v-'
        'sKitL+oSSNkVdZ!jOgKc{}v`@#O1`rvwieu?k|eyaLn|Hk(|{hI%g>bv*<e>eCJPrqEhZu15H8}W1UJMb4}J6C^t{DA$c|0~L&$-'
        'kQafc%E$KfLespSMnPIskr(|9kdV@#+0P-FLQMrT@+Ufc$;?1pYVuC;flsr}%G{KVToW{=y%vXRHrI-'
        'mRn3mogv(zZ@q$q%mrLwhz7&D>;KK_nZcJ)|T#_GmS53&hL1WzY8<-7>Bm2Td-wfU<)@#6Szk*`Rr+C_{r1Syqj#FtJ8RlqA9o>z'
        'U<QEHUG64cu32m?9r?L(3Qipkn6S^V_EyLwu&$B)yeqXGs|O?>^=Z?PoAHkzZlHIn`G1|n1br|(%HsLPyqh_{_Q0#*Vid;KE@Eu7'
        '!!D>k18jclxfQr`E{!yI@x&3q%t<1BDgUg#sLINd5ArEBz7^3hr6mb;JLje%N!X(!t8@OL9Jh-_WO<CEX05@y8H^Qw>van8g5e`i'
        'D`ZdTMX2AZ~XtZ{^j^k&+##L;qqBs&eMjht(p?$-pR&?St}rm<B0?Q^lW3C9z(>%-BT)!SV#zRK2;xj-'
        '>&bJ8}?NtN#XhN&qSopZgm;4b%_jp$+^PIWe;Qe-XSQ0RS^9JhV7^OD{^D?VShX+QT3=(5B<TE?sOE7{WYZpSA&MW%>CX(9g2-'
        'AMg2Z-'
        'AjZ9>TrP8AOQ$G1+p`_QmD`)aIXYbM&fmCy#sD+|5gE8oHi6D7JW`N9zV4r80lB?^$`A}kEf0yU0g3c<m7(fAd(CPHT39Xqaw4Ph'
        'Vj54Q8(&EBm4x|C1^j+Lw!M_y!Qpu8@Q3xPrM5}R)F$0aXg_LHHv?8n8P^5bdnfGD);p3!+8kX$jltUM2sH>dXHihCm-bd@@SE_i'
        'b?>9_DGB^obPy=#&M&hFDyj}?e?_7CxkN25v#!lJKjW}qcX9x%_rNl>)S3Fu`P{p2?qFyH<ee40$ep=bt1#8I=i3baZafoz$ZNMk'
        'o`}|*A0U5aiXoj#W?nX6`mf*H{kNDW7FG1NttEXs$st&l$Jk<=qzJMjD!Hqojn{<#{uUYLsEru2Cw|7|4OYJ({;Y}r3@ki(md*q9'
        'SjKpxP1Xg1V~v|!E+{O2T{DpA$&+76T4=mal$vIq2pVw}BS+P)zL;{dZ__}KEh|JbJDSWaTgTNC(n=56HWdw^AQiPngK;+mX!$%5'
        'm}D&%*8NF;UKiS?spQ!TPcQE0F#=$=WhbEN+ly<OP^kXP?H=Y3U!*tVklzMZ|L9hk%g8W(4&AGVK4L!wn(uugYs@3TD6G=Zj%>(j'
        '=PQvj#WeUolmwdl&ANr6N|G1_A(ytiv=%Wat`p#oW3~J3+*aT+Yhc)YMl1}YG;MzPot7jlfy0#}{J_`R>#O049Cl8lDo^eh894EO'
        '4AL*!r*L=0%oenl>zG4DSy|1`XpJyH0)mX(FzSttOOM}+w1gqlx!iLp9?&=k4B^oXsBb9;pfKIyKrFZH7{A9_2r8@L?VdO+VRaTs'
        '|ILK7`dI;kn{zQ;h{&NQi^AvFAA|NpztD^fmZVUssiqlLiRjn2yPmt4GqERqP^{^wa}{h(l*llC)M-'
        '8W5wM4t`9E;)j^w*Xo#_oWyaaqYbmj0x+F3t>V}Cq$OaRUk01&iX{^^=oU#`Czn0lsQ<!E`gc6uVZKmta&P;ykePfsX5(E_WREB^'
        ';1z|+%P(2NgRo0*b{-CTv?S#xV%oxY;%KDXw7M!*~xzsF{aF{W4LpP&BM0md&4-SDThHk)0R`13%-'
        'txQM*M9L+eH3Mnu0N}r35(@d0GB{ve|MWydmG_CH9hpy5$p6tKV-'
        '|Gk%FJ){!iJV~*_X+d`A(+sb8^eS^k49`UM8l@)>zQcbl2~mO4s18C0AZ+{<-'
        'Qw#4G}r8k`|msi2UQzv%qq;T~{g>aJa0goSo@9UR;4<tzv<J1uzw?wuWY#j}EZa0jgmTa}=mY`*mbNg{&$I2FPxF^3zDD20*|cE#'
        'z)_s`aecUP91H}!PH@1GpRYybTTA@V3s$6%&nZRIl`a=+~s4Ryj<GH2zHb<kSQM<qJyy#N1C;@>CD$tw7XY7G$hvP2}aDQ7V-'
        '7Ww~R@)GTkT-'
        ';nRsgB%eTd{^|Na(w1Xy_i^ZJRoz5@V66w+4@}M!dd52TCB{9Yfi=g$N5~mv~>ObMC+7O<(=OJ^p`R(m5+9Rwy<G6m&(zBCV#OT7'
        'CO8K#fQY`Q9i0^`|?dK4dIn3m6QD6DlK!6HCSy|LgIeJY#+ChGvwwQH#OJ?OyK5<p7sFtOIT=k;PVbIIWQ{RY<(#(oa7ZtF%vRqY'
        'lFH-'
        'R>VjfE&@8b9=FpGniYVAu0>^Jvbg371<@5IDLvC6a{|m?6~pL4X3YAjW+YLkfJ~=Od4T+4WXaB9G*ukP+s^ri0MRD0uYzE(>V?Op'
        'NVmOg<$5JqZ8jLDV8^e0NztULe*DUU;q'
    ),
    'mipmap-xhdpi/ic_launcher_round.webp': (
        'Qb|TeCJq1qS4BclR!}%t3IG5A5C8xGUjP7K002QuP)G~}0004?L~WZP$@(JxxVCLuE8Dhh+uqr>ZQC}-'
        'w(VR0AOCmJU0szKtGkMb2|xv7N@#IP5%mu#0Kf`6pMCGEe{}2ooyRWPV|4+56ze4dVA(_N|9uu)n0r5U;%We*gt`O?z|v=ZGL<B='
        's^un4)kyNMAFo^ufP`8IfUTdJNYXSrTj*Jh<g9o1Nq|%@M#y1bl2miH(X*2L<J|cHsaOJb|AlmOw%yIh0mny3s89sfd6hI{MYEFM'
        'ZUabV64KSvm@_M!jeKZPq-'
        'q4g`rnhrif8A*T@hmiLcq~esm|&vc?}TT7BSl$q_LJc^UXyeZ4%7$KGj)QWv>;H+9Fu?H!5qa9Jv`%8wAVsrn1(?$(tj!EMmDnRM'
        'y-'
        '$Wiv>NLYU(ZDr;|?v=XExLDKtF7SPyxi4a?na5t4jRDLQcbS>dXHdx38Z$#=+#9GtMOX14BAzcVE+b=X0GyAxuVr))uHI)T5z6xn'
        '7hE->pmxRXMA<YQhqOqvi`_2_ZXM&w*EUfWDNM|wq>BaFpd5I7^N;rhZ;wrC0>L`Zqy+GN=EfB(g1e-'
        'Fmz{Zo2I(mj$rr%Ql5U|)(dWo3183af;oysDsKZpcGd`2r%=7@O_B9@v)FB3Djfg~J4W1*GTAtl^LEtT<W#2|mtO68okIIz63+?h'
        'K8J296_c|LF^wPX(g_m|B0HSlK1GJ61jFqiC4pj+9x{U54(@!q4AtOxKYwOqy@feTBfd<xi;R<g^1)t%)w?hVY|kGWLNzm|vKNou'
        'K#zs8VoV!71sLW)@BFE5pG4<v;63$0AfiHjg0;Yw<m)L()C5i9@YUZl+3kpM(|;8vo{L34!wAYpeFNqGel0E94mFVE$1pT0EWe~@'
        'rCwLHqlAm}iJd53#0jb~jW#Eu|1mR1_&?GSVx!_Ty`<UDS%7@H7m=7mw73_-Jkhp8no{tzWJ72-m}JeR|*u^t4?3wEG-'
        'F&aDvg03c9%|<DdFCn4JA>mzW8H{}wjInEoapB&y668E-'
        'eF$0^vFsRH{c`435VTgX*%aowdFD|_Xm!HolWFzJ&ZCjg`h?BKQ|n~RM`1R!GhwwpY}7|NWm_b)H(}`yXkHIj_Sgss?H0)Oq}IX6'
        '7Z!q`{V`zw(agDOuAFrqAgE$USoQ@{y-Kd+*PB2BDk{J}-'
        'AMJSxRE1Iix5;dM9g#11k!R9vXXz@x)cymX#tkKb_D6_?QzTG<VV&85~>~qSm?B$NoF-'
        '~jc3gy`(3#_AOSTD0>mvJ8cLE`)pGNyMv~)R*kf)$B5E2Efcdt)_UkEZ>C9j5+GBA5DWb+f1OS%U@q&lH=+^WPPhGa>@&F(bQ1>7'
        'ypw&qN+7DJxI3V;1001yD0G$CUU;tnMJ{byxL7@dYyHW%IVJ$`XxiXv({kxp=&3O;wzpx(77N79{bH8vuxO9RVe$YPq_YL!F_0!s'
        'Km^bN{_s{14w|%{Qz<#@a-g~frzW(LxZ_oqu&#epkhp0d6FQ*^-e{$d2-'
        '}>L{{scdf|9k(x)&as}{PV(>>|feGnYxj^Wc{wpPWMm9Kgw^w{haMh{rmDG_V1G?k^eIP5&1v;llG6&1JO?8Z}VS|UkvzW&=dIY_'
        'HXi^Yo8on)c<|_s`m%<hx`BXUylD^U&eo)f2IE8`?3B1|Nqp7uAke#WuMhEGpiFiplOO1wwAm))07L-'
        '0GbMot>^V0qwpTQd=398y2Px9N$XX{R((FUj(Y+X|DjxEun8+LT<NUTxVm$OveEw1dq6VXJ<>J7@4Ts{lt$j2LQDFmwbUXVo|YTY'
        '0T7BA0Q`Xxm?lc<z#cGFOU?U8kOjby6gC1=X<V8Y<Z!Q<EgpEyi1v{MoR4o%E#h19q^E^)559=nx)tz*&_|KTrRrQ;1y(=+0RI2Q'
        'u)hE6DZtwF=KS^{e-lwH16`+I;_)2+2asu$LC5u+fJb5ngZ%!L{-'
        'M|D9%L>VxCtuU+EL!!4dA_5=@nM|v1$Vw!}RK;k7iH{z>2yKZIAT=*XJySn$gHY^SBNA8fnQ+FTp+Q5x4A?A9sdKQ}G5Epn|E%1Z'
        '0N_Ufrlp<Mzc$_-*<?zG2<OviCMjy;77dg;F(0J$P@oq_}N!u&1YGxO>y;q87raT}1^1XdNxK-`ztH78_l&;^t5RTAAo6JX-'
        '%z_x61XH-0ZPxUW+7VRmc~@FoHW_fW&i2(lj)w6l9l-+7;iYi_FPI~pml+imKR@xKrG{;&RfO96=;--'
        '>V{&spuEgzk_#5_xaoicbzau2lVUMdjrGhUkv=sbjh5FkJHqN<4y1Ijy}#<Uyg@XRSJc3~L!4i=)@>8eiKw2q&O2#4dFAW0M=BK8'
        'Zu9!F>kMI~+p;qgERA5PI(0vOwFw=3u{ua{KrT|DP5BNa-'
        'o=K)q}}$D7?o4F8l5ECMzDB4;vR+}kZ69~MZ^=u4QcCE3!`0mbrU*<{c&pg+>IS6|8rqfHIYf33q_J}PEypDEal#?(eW^NE5*f=E'
        'sCnOf3{sWzZAB;bRW%8fpB0};<F^rSdwoRs;VjszQ%Y9_FI$zR%M=9P}lYF7XZ`HtMEG`N9vp2Drh9^MHCIj@AG+xV?BCePp?%VT'
        '&nl!0G^&D8}8;tN%w+?h9g@r6h|oKXz&eMi16r0)T@w5M)tYbYL!BLAb;iQQcmuk2A;xqyMlJI~!9;IyorC0)2jN%P_qQDnJUeGQ'
        '|}D0IKUPvurF&3$~zl#KX=|3LhMy&@bT=s~}Qw*-'
        '^JN#it#wPI7%77HX#58Kg%krBZaCSPT_j}k;))=7GJIUaMGxm>362|M&)=Bu(ey}p|N{~<AT)dwJiz3++Sxd$ZIT=n=QW0d3ow5h'
        '%+_ryi7_J8}=zrW@l$}XES$I2x|kO|Ow&&>zlTq9XmJh)C!KQt{Ryn<$Xv6MNT1sOK(oZ@Jl`Oj;{yky#Mdhi>A<U?e)wxZ-'
        '~U^LpR$~#|G1m;ffaDl9u^AcIYc-'
        'W+qmc%WRK;a<TES4J2^(&bCl0nnyTbKclAOfv|uWpkDF3gT?;pKCvpr32xj#G0!DN(iKqGs9W#8Yc5Egt`ydp$K;q{v})d?~qXl;'
        '{g4qMc1=Kc$BbF(%$EH6CuH{VzLq4tQH}M|{>M_kw?w&@(j~Zyh)W-'
        'az182w+<T5unjSxdESX(_m<XHv{l#hu)}WfMduK?#53yKCwL&ntpCl=jcAOIV4nJa!LqMC7uloQ4q;~U&wbUzAHughxooaP2m-'
        's>qycC#0R{zSb0iHY$P=@rm?C*>ktj~eeDq_e1AoWf4tQrPqL^;$Ik~e%A{fEM%ZfsUD?*gB=IWa(`1XosV(1@o%vD`E_G$=e$u$'
        'u8@aagv*4V4!JHYFfM_`t;j?9^Im?M5TD_a|GG?)-'
        'hRe3Y=3Ym2x8Y#<97%|;ow<KU%ywMtipiZhNBQk~u0UgQHot0SLg?mu7DrXTKB!DuR(3wj6u%@LCuV)eV1funDY#WmdA=EZ0CQg~'
        'gfilvJp{eDz5-_u0o)M6pKWk!{1iu)K^k0-D#fUNHDn@{$NmHCrU9qJTW_ilKC~6RhkOnG{?p)?+h=k|sLt6%6-'
        'KB7^lpJ3iL)MrwU#sAcLqpVq<j)KH*tjVE&@)gPxQl5m$>3yP(XPUi0NQ-BgWdmA^e(jD6`z|b0{fQY7=BwwSuzB`C;ISqvwS4{e'
        '@0LpBZ{lGLAb|9&^!fu*Y8QW+EtcH4zLOtvdyJF~Nlu16<O1A*Z4p_FrbWE4Vaocm9QAiB7%x0PY0ZHF#sKbce{KkY9^jFiop-'
        'W~ev5rwN#9(6N3TIllxS@b7B*A>e0CEW~A9<F0}|t|!C7RHb<h7V{F&@~iYfO`nZIP^;es=vZ?hpZXS{flu@1$&M4`@jx7k#Km3P'
        'VR=2+?JKgP$NzlbuXy3`S(PNeq8$z%g5&}H6#k8!H=)P*fo0Ao={J6<Z#YKK0}i~a-'
        'ZW6rC;=aPpW|N+d_8%Yma$y*<w>q^;DO4vO>wr;6u%C{<9mUlvD87{*g0?~#&|6E^A@nMG9RX^VOqq<eEK*|5x$mCT;;^~Ml-'
        '9&l9@dG<kCPJV;NECL>?+__yoL%#uyf`Fq$>h&}`f~q<;@vUzg~ESlC<;-'
        '`AnW?#_BIO<+*%cXP<QIqiOLd9q=@jk9~%W^enwpe0bG(bwcIX=7A%53oH^lXC)z9j-'
        'v@TzNIzS<poM5MHS!0p{v@wE^%*;HHC1>5n>@)R$`gk5I+iB65;(J16-*5EDeou!o{?xr!~5$$H-'
        'jZ%lwcIWgdX_RwR2lOEZ%%$ZNfE8JoOG>eetduVm=s@NlTH2m+~QqG3AGCq;K9}m!U{vcJR50gT+0)Wh}$|rkQRV21%cC57t7j?('
        'TLm}-4OIw_X>1usRyje+0qLa1_BA`HY=Y=X|8~(jI;t)N<xW^@Ti|2GMTvNKh-AswG;mJR})bq9T>$Fet@Qju*mlDu4I3}F~<6GK'
        '5l{9@`5Zs+*2_+5i;EP3^xhJV<PuA7B1bZh?-3&-Jlxrpr3XvIZ_$d2Nv68=d0UuCj30-'
        'Y*M0ls0*vO<F|7Q+9xnzCDXR(viuXIgnh+#$@<DPE&nu6FnXP5fFcu>HU{3vX(3{I>G{mu6ZF_&;O*#=#!DiH0y40BqMv{n@FKmW'
        'CI(v*$)oj%G}=o%$J000'
    ),
    'mipmap-xxhdpi/ic_launcher.webp': (
        'Qb|Tea1Q_gS4BclR!}%t3IG5A5C8xGj{pFV002QuP)Mr+0004?BWv5@#(I8GwL_A2<B}sgR9{ee14GhwhSoqK#TU1rXc!_=bg{qx'
        'djnJ3rT$Y##01c9$T_m%W6puA8d3t-n@rnTyOC$@bg~DKQn(5s0h8mqzpVe#2LEgQ%iZG%kiw-UXpSCz(Mh+B?K=78(NP2GazbS5'
        '_DYg<=B^FyZk<V5-'
        'QFUGOGq$ZNp7w|baQDnhtykQ{7mYK2DEh2voWcs%)tj)(ZCkdhXZmiBNmcrfK6I3>S4rErD%{#(UQ@HG7Fh&pxv|}Um&rRxdz)!O'
        'VYU#`zo#h_o98$IYQj|T#5$0l+QacoE3Q~)4-'
        'cv63<AqG7Y||C7lvt^V(~`UpFzF$lQ>r0!=r_KnTq%FEvp7RTBba4pmfzMTcZaJoT;)I)6$cvi((F2d=N%#LQf#N;J*MnTOuhLgx'
        '?3Df}s`1=F7)F<#4S!L=U4?%y@>_byDWs2Yn+;U`%=n0|s;UCf}Zi}u=o*Z#Yn)vPXN@Kas<1XC;ZP;3gjf6HsZ_4h7}*EO*olfs'
        '{}S}^??Qs$v|wb1!Pa%L{81=E}y+5Rf81J~DWB8jKo)j{V^Nsu{Ise__JGKA2)@=^oEUo{~BnH#biFx?;ngxI`x8$R>bO$;YUw5k'
        'EMBu<aKlntHfC6O~j-1%I}u$A(8Cx){~?5p^YdC@+J^Cp%uA1*g7Nt{2kkoi!#X+h?qBbF*<m`c%-'
        '5f>k^kZg!dS}>x|%)tj)8Jc4Ha6qQt#Q2%il_4pe^lVI`?*#Le<mSWR=F(~oiT*=m>-'
        'I{Lb>_aw+^sW7tJ_<|z@;W=jvjr{Nw<ydI{D?%Q3Hv~4hfhX-~DC%mp1rc>tF63Pk<D-f*~b<y~(tlwHtZXPA7W+DFv=-'
        '$T_m%W6pto0RUD|I3S)3007WB0G$CUkN}VXJ{bsuL7@k}8Uz4gEPxqZqz7i0PV+yJ-;f_O_J8aDe1D#Q-'
        '2VI0#&7!^`zQ17+`sF8J%3!ijd+LuY5rsTtNq8iH<(Z5KiWTPJ?H%FeLz2x|4{$c*puiF`m^bu|3Ce2!ME&B{x9-'
        'h0w2wPwExlk|Ly?lH|k&Y-'
        'rfJebY}Rk+0Wa3+26)*RDWE4`}u46E%Kj*exf}<zZ?Ef{qyo?@_Ui0$a(>H1N_J42lnqtO+;{0{RjN_<wr6t06(06UjL=`-'
        'SoZv2mFuopWlCQJ*NJ3{u}-m`M-cq<p0qB*#B?+-'
        'TyKF|LRxPAMR(eN9*y^Svu!dh!Ye8Z8f~*d=xMbV`3anRZ8xG_Q3HWb2tL26P2IX0{Brvo?<I`sLUxi&Slb97Q%b3y-'
        '(V_v!9{AF=3|Ltb#G@dZ!|q^lv)L{2VakXq2a=?%3fTE+9jKy^Z(aNtxlRPZ{3xi4S}4{W@9lDj0sQ)upHR1j$exX*&1be!^N4jj'
        't5U7%B+L)2+G#1Il7|>wlWZ(j#iwcOjls1L4b4Zve$MT;<?m`86N4SbD}FDqNAkD4P5U#z_pHydJGZ2W#MlH6Ln@fdzYvnBK?A6h'
        '77{0092~@ooghns^N(;A!;o@kPD@b_@nRrLzmRyGJB>Hdde#t*msR$T<?Q4;-'
        'eue2YM|Hal`^3o;5Y2lA&8wM&p55oHPnK>qmYnxTN91Z`I>n_(J$L(M%J=--'
        'G(_=eh5kUnuQnu{B9?f0XS;FBWB;r@$29OZjG5tH%(H^gY+e1{ah=x7C5vfB}z(Z~L@?qC(sa1xY^T6#Qd)yjIlt4A`lECMo72I8'
        'UqB3d-#2it}+8i-*-v=r1_AH)U`8?Upv5G-'
        ')Il>OcQ<!l4gZ#%315emR~7Sh`+PfBtHh|6dnfGKLzAVk6SdHy~9|JN>K3CwCPy8#81y_thaSX|YUypPx`x{M4rP%zdkC$BmwcHf'
        'jY&MttEe1|huywBy<ALFmnCgQxY1^Q?h)U~@>NrkEIX{yNBxm09&E)fgo)#>CC{6`8U&gJps<hBuVy_ip}0fXdaq&>j#XwLxfsyE'
        '*mgvhSI!cp#~F6J>3>^&=<9Et_%TnPu(DbmG=HjD7a(b5wQyLO-9>iEAQJ$1}g6;b5=NeQG??!#$)n=znsv$10(t7hI|f;N#AC-P'
        'GF92g7HAH>88_urJ{RcXyX6lm4hJ`PTM>4Vk;ZbreCLiJI8F44=Cw4+VNRNpHsw%Y_x1VN6wer01SITfQLX9~zSb@F{;)d}B*CYD'
        '-Ifk57g+tcS0)F1s0G#nk+7L?nk{|8_#r$NV&FnmSoPyxjC2tQ~n`3z%BzoNo`F{HQe`ziT>A)>6)`htb(cs-'
        '^p?!;}VVv!1^3BteTi7q6_G)F9Jb4q^;H(y4pfz?Qvq|7AJaYKjX_1vY(#4)Ee-'
        '!zebjE>nl?vX)7itMqQm$B^`d@0@;;RSIzfAG>~(Da!^f1O|m2ARiUzjRpBb9^*rk(B1%>3#=pGE9602<5}+1E%;C>b4zSe}wv{I'
        'dIQ~I^HXQa`Jr<p68_H7Tb^24jR@CVqj_Wm%_k4Wtx%{-'
        'T$Be;LU=ayraU9gE@Z&7GK+^vnI#t3|kyS3cW84VRz)~^{ZZ2u?~sYZ$Lu1eocQ5Nu5m<l(r?-fJC;uM-%%_<am<#-'
        '{SyVPIs6X7&(VT+VsSo&=N$g*%cABc;-dSb-rDsWB+?sM%1sJcport#=qK<Y(?-M01Zn<YY#WD0HA-?=j^Bv0fo-bIE+KE4UDk~p'
        'XVhD>vfw_?NDt3p8M2ic&{IyhvMa3gA9y}K!cw3TS5UXqm$K+8n43sJ8%In!I1PdOG}_%p?yZTzIoo()6KXs^q*U$hQfg3puJAx9'
        'mz7O;HH#RwQ=eZK2n<+S3F+aBqXu~%kh>pK86+Qf3OVY<ldPU{ERjW?etJ;|LGhWA&ra886YjD#3%@{{YxOF*MBmlkIYA<9uV@8A'
        '_e7TwzF1MpMUV^%D}bY7;PnheJo##6<NvV9HR{<=D(6De}v5MB(d{{rxPc^H~Sez|82^)Rg-'
        't3*SPN29}TKp|2K_ohB@z5Q@?~aHq1Dk6X7GrdeeQs-'
        '!hM)n;tw%)oh7SDS^b`9PYWbL0^aTYL*$m3IV9Z1EWWdDw=`J&)MH)#KvcLWm64Ih$mI7z<qf?bR5LX+mDP~XH_Af1s1-'
        'y5)Bfw^D#x6!ZcE>As;4h8bSnmcCY5%vEJ53xW4hSu<+5aoMXcF6T4!i6}pTSZqHv#oHX>f$kSiH7bD}Zvy<h$3$VirSql4kdU^p'
        'DULEVW{sQB}^qTW+Zv(@TlFC+&Jo$38%@V>9d^I$JdEu^zZUqwPLXhSa;=FEgqeub4VD7`_VjUPlZ;qynE;G$l6HyrzT50=9c)`+'
        'x9Hy*6t9%TzK_m+gsL(gGQDzF0NN4YBsHWGh5vRfDrZLEwNU||+KZB1)W&RIJibK2L`(gsok4X%FgVr>b@<yShymvZ*uJ&wVIS7m'
        'iTwzr#=+d<=A+LEn?qoG_L&`R&vzb8p$Sa603j|T*4&WYmG>>SA{AA@nHGxB*BC#h;lkS>Rjo<sxaVxFX?!dgziDQ)m-'
        'V2dYb14e^!MuLZMh4nOW(^#Ze`K9h7F#m2tv(Tc1k#-'
        '@<;Gpsp(tQF${&@6^#B~T$t!_<q7+s*xHW6lCM6?JedXKVI>MhRS5Y`PC<fHv-&-'
        ')n;*Lt>EWp1`<ol)FR;F70c;S%gsF@PrSW9C{fTFFc{fo%A3var&ut<NT%WZNA;02fy?<DZ|uJRueb{M~klZ>MH8<A!|J#Q1++SR'
        'yTSoFfE(~z|~-'
        '*XO#kJw=u;|h~@s)Qz8x%;kium@zx;|G9{N(YCy$blH2si+<S#euTHvsZpxnpU6}v8}|bvrRKO+!?oB`;Pt@krkyPbTEqTOl$$N&'
        'fp<9=YjUn?d}YoL0gT`c$^zu0>Ma?qwm9&8JKIR3EZ;+f5MB3ZJ1B8&s8EsgNv4ZR>7yovSP87W4F*t=YlU~Nu7|3l<0Y_3TXa(9'
        'Mq7Rr41jNqX@<hM(mv2Np8Ekkf3kdGg!aW%=_oS9{LgYcaV-esm8OANDga{>)SzR7vt$nA4*v^XtKV)zvHG%dAIsPLckloyW5S5y'
        'qS@i$CCPYBpoC}$)ESIY{ZXsJf{a%m%JUahkF{`?DVGZAxY~GIRiF|9l(2u5kYCZRsP%mQ=-'
        'Q!O;Hr8K5>WSF2xW1Nphs?;xH}4EuQvTAb3pU%%8&;BFU@S+L`T`phD9T1o{n%dNY-'
        '0T=+8JksJ+KBZPaK(LZ^GKK4KUXc_J4u?KsHZbj{ScrCBv#}vfM`h<w)DS-'
        'x_KlR#DvHC2eCC=V6xOdzXg(_Pc5mY0@mjBp?hlEt(ix21wi_*fO!sW-RQKKmhAWAbvI5$(*^l~ChR5mK2uj_p?!DsGYh{b)fRYW'
        '3(#y%BQ`Vda1kMe&qEFR(;hoh-y|Ia9+PjF%8O3GX!df-'
        '`TCKCZgzZ_cb68Qr)049@agYAm}`oi_^)GIyPHME1R)cuR0rjU|ZDkln*9OTZ?9Ca?t^3*u0$yuEjA$)iDqG;mD99u-'
        'uK5BLaLPk3W{^N<E^0D%yuww;XI5rvjDH^H-'
        'KYwvtF7`mp#=WXVH~$3(i`8HJ?v1nlU=S$dxumR8iWXI^9V@4&oOmpML=@i9rB1)4pnONk&H1tnv7CJrB}R|=BSUVw?>u$Y8Qso('
        '&oYkzcHkH|H1U~sstNLQoY!z41tSlhl36yj?}<%MBq>SMBpbU^{abc}AOu{eS3&LCuZu{2wgLu(j?JIPuWQffLB}5jH&-'
        'mI?oVXSMqtLctP^SSg((l#lsrGt&cu+6s$$TqX;!s<jG&u%1550Epq?&MT@;w<1%~;pxnl8v{pdygjb+r_WZp-'
        '$o2ShyrT2N4l%R2b`*+2omBssNl8s;*_hN;7fgaEQ)Vp3e_DJ>{j!pUrnr%QE+#3e&ZoVzn!-*RvOieYM#QC-'
        'J?GY<xE<{lQ+&JE##a;&>)szUJC_Ac&Mk8}ZB@`9sJya=uO(VRA1!;R5##PFi7%l|s%pT(}kt5&Q3aWo^o;OlKZ>2z#5mu#oQbxJ'
        'PQi)q{!ZpbvibnBrq;?qlkuib_X0}3aazz-hYD%NT#2Mu4ZU6uP'
    ),
    'mipmap-xxhdpi/ic_launcher_round.webp': (
        'Qb|TeLKOf2S4BclR!}%t3IG5A5C8xGj{pFV002QuP)Jn<00057hHaZ6N!I(t7ujp?U~SvB)xCRc+qP}nwr$(i+V*zM)%8Vu?~kr2'
        'WJct_b6pWJ0qAbfCMu>X+QcBJYlsmeH(hbW!u-OR^9!f1Sb>omgH%E^3IObU>a#!i;~N$^@#0;-'
        '{_=C~wO<5)s8YTV0bqxFyz@_MIMUOEnWHcI#3S~d1E4A;6BR&@f7!2=NHUuxcTVh{k|mP#|Gf2{TL4fgRfqugedE7LGFf)cHk*;;'
        '4WBq+4$x4dpuqYM{AD8DlCzbbEs^}+OST0>OA{2>>BX0mw9Hm}a`KLk9s!7!L?W>NM+am|&i3a-@+ap48j7L7&L1-'
        '}Wp>n)lRrHfh-C<hjb3sSnVeltnf}q;0WClT?)6VHvGd7!>q{D_bW8&F_&RCM5+?F5=K<O&1s;DVb7mpk$oFiD*rAA3-'
        'z1F%&6yV;g%CO-0ViEWbC%VZp9E+p0`OcivAEg!>6M5bP;CAY=FAcs|8@Xk>mpYEokJGdI5-'
        ')xWf2GcjYAeYad2N~s~ViVhKU7t=L-;}Jq=D7FtO-'
        '9<O>j`EfJ@zVP@go_(H^%M4UWeX7Szl0yM3N*l)nh3i^<bN7I6UmH%L36+I13hR#f6<G(SnlFq@=&{?T`l0#NA@uJltvx#^Phped'
        'a2NGo#iWA(tCLHo*h%*SX#kI_=s+*qyoth}V#l*^Hzjm7trloisjny@N1v;e=cD*ZmeK_QUpwm%&o5l)fzj>1orlGiiiB(Q~FLVl'
        '`8~@L9ojj$(L??@Q35}Ib{0+iHBHP}ay;jV;2Xqp}Cz)6;zjA{h;|1)!lvr`&<DugzKFO+OzhWbiaRRnAXVnuQfH+RXi)oefpT{t'
        'U$hy}u*NvG+Lf58vfG1Yo`0;T>{=n)vZF_`K0ehHx?Pz=q;;4u>&{+M%KZhX8M4Ahk>&Ki9fG$%U=b1gw_;SQ$5ig_lfy7@UEDQQ'
        ';ras`lxDx^pu)~nv2WWgCA`o#;H}-@NjF5M*CuIIpmgCP%{eZr-D?-'
        '5b1A0$Ld=O&9nau2o#y6sA@C;gCNc;gb;)6_mA@jlwMDg?f;9Ob>+5852UtmtB0-'
        'FzdMB)X&5yQ+LF%R6GsZT5b^Sxu?|1Mn6J5JAiW5pu9XWZ2%d;vj!$J7^`OFKaEr9N@}Ceq;fw7!t|b7;hUnEHb8Lx_sKlJ|$lqY'
        '*S0G4}+|he8qYNm@V1ykZ>)A|BNjj9-KTihZ+tPk0g{AhPa-'
        '%zeOfItU6N;_b9PkohkajJP{fA27ZTx=gU~4a_|t^R!Wj_%yA4nOCg`8KF3VxqjxaM8s%mE@i5nI}d=aMe&mQCI6)ctTkZ8UGBBx'
        '1&C{d;^S_0%YMm5B4Zs$ubc7Nh!{8Mub67)zPLTYSc)_2W_$}2<E#9dsa~E3+e(-O#}6x(_%bLaReX|GtL#_J1(_&>-'
        'EPZXsl*3DF}dOev^pjJ9EvH5HvjQdBhPtnnF<tVu}a1_K{4Hk_tWZ=`S0~qrX*pbOFh@d&5wm*+KR)OyfQ;R3lY<gcru4|F@8;=%'
        's?VON2^KZ<trs%mO(cEJ5xQ}1}8u<Tg5&DdNquXMZ~NXC*PI462=#x!R#B{o90y*@`H$IV}lpayaL8=trw*gP`r@l#T)Y54Fv6!h'
        '!=3^g<Imc=Om!567d4M7tQ#sISFX7;)w&Ma=G#Sa|md4#K~)DrOM<BAcB@RIN@I$mdQAHJffiW5i7sPoC{>U_+&(MQGu6|R+^mor'
        'B!Iq%@A<TwKOk^k<SJcosHP;3uG!sBL99OLO_QVc*yl+Dnrh+H*SE4Zij#s?=t4xJx}CM4geILSK#QMk(RsVMqcz_Km`R91@3b(n'
        'R0isk+;8OLr6d&L%@blypZ(dok)qi{mnZ8ih?Sz!GnH6(sJ9fk-YG^I{_*vszd<Ceq=z>lD8&XCi#<lZ3t*UaU}|{)8qe0l4jXwm'
        'Xnd>WiLAnKny6eDu9Dt`l~f0nJi_Wj(ak5lKkuY&e{MF6_h(f0NCjP@BgQ9c}~;h$jd+XghK^D3@Ckw0zmeB&})8l;UcHHbp4Os|'
        'Kvl~0RUA&6+?_zKDXl3h53bv=eOS&%QXf;MJ2?jn7YQOg02DpR!}$~#tr}gkVF8T0V<FHkN`dz41__U1U7-'
        '|1OQ<yz!`%<ujYRhd$Q#}N`AxpN9)hz2hJ6%`;Xr5#$JD;4cSN5|0KV_fB*mg_oL_o<=2>Z=|A(&%kS`=**wC2tpCUVf$t^$_x)G'
        '3AMswGAEQ6|{i(fKJpq4O{Vspz|B?7F{>T2;{vY~ZfnVnT*FW9<d-'
        'ni!FZE;jPi%kPe<VL;yLx=j>v!!}K^~3qP4(05f0uu_AL+Ug^&#pJ_>c0B?%$UGko<p|m-'
        'z2MFIPTg{+IiQ?q~LokRO2a6YK~2KX4D^zt2C?epd57{ZIV|um|#Q>HqP+Ek0L2p8tpb5Az?|=jVUmKjr^@_yqnx{J;Fi_W$vp^?'
        '$~H|NqVR4eLAh``Fj@Rp6^|e_BFS)j&`C{3+ndRMU1D*5AoupEzdni|IYrAuNwwPMjyn&?YpuA_8}jUcVIJd?^$=e}@fsXx^0!#6'
        'lrHRx)rLZ6aumesPCA+kGlDdKSWnG&*{tObrEYj&YTJXnB3P2P-}%ILifDZ-'
        'n#y#%^3rw=Of+(!IC;!;vFdrk6<Ul_GnNmgk=;k=@`OR&EfVBjGT;(!~dXEDVBYG7e`pk*?_%dIS=sqA2ONu?@52qA|ViLUpmNr2'
        ';Qz>WQGTXN#^KKgDn-iZ5vg9NPKFln8Wv=#9Ae;5E_P?{r>JR}ArY#pRVjAI_+w(@U<28m+YNhkmRYFnW{I^Se*G0092~y8m#${i'
        ')nAeyExq>M0}%ewF-}pqqSOaIIj<)6UIQit(k&meudD=UO0*D;6N*CmCVKZ7E*^D;ItBFjb~URG`>3Id{MI;BTXUtfU;wVZHu-'
        'ug-oF+)e|~3}eDHTJP8raq^L~DO)XZ-'
        'C)6vF%RVt73Zm$HrKS6CktRqv3Mhhi3!bjK}HQ0f^iL4l@zSa4^=cot%ho}F3|XcjnEajrw2k|_wLCNMT94bQ>~f2yG*6W`Irx4o'
        '0M9g5AV=TEmOo2S4gRE!XIr1D17g9Q@vX#xj?B3y#_x$b*yj=UYS-yfg^NjOZ+NOD79Gp6<#g@6HdS~6%hm|D&&1p8x~c0qTnAOh'
        'kL(8aeoL-596?;$VAuKaMqrO+t_Wn>v`#he#sA^qD$*q)Fk$JA|0aAq+vIkCvOaLQFm8Q^z~2y%s;JGbB7-gtN-'
        '+a6EKLbh!o&jV@e7lyL+|lu1y0;+j+AtQj=;P*VyO;|3R?y@J;G1PBmAH+j@vGGaLW^zThg+<xh|SMO^%zZLd=Xz5MP2{h2)oi0b'
        'q;NfV1gvC@Vnd&vxK1OkkmqXL$Qcy5Gx9>e+?$@p|2Y`fHRAd#%5(*K;ikXa<LDQr<o&BgN6!FkFHr4oS${%}!NWCA({3Lg^=61E'
        '^|gqi)RBv616g`2;r=u~J_mRoTD-07i3Gak5vhUdELOO<tJoI@hLFcEO{P;*yYJMT3%+Ip4fpt7_U_8arg{PW5aUw^a-'
        'h|^S55s)otA`q~GRwC+TKGU|+SpW1br2ekubY377lPGX@=@v_!0S;bqgw%smdb~CwZGQwqdnL?aD<T!-'
        'Ku<;*uihg%{u>V`je;hc`}cAia$%ux)x1Vn!$#H26(9j6=~m5%8t)EEmS>JRa6Pj}hLn&~`paPJea;<c#eU?U@S7K4bHlzoY6z3;'
        'gfu+@h2B3T`7{$Ae*;3yO8BlS+4IA5wGOxNpCOm3Z?5q2v8^wOMt1zPNnKLWv^=JUZ~p?3r8aYQ(r<u20RXX{jz(3dF@Gy;z#MC('
        '+#j9szytuQTozB~1CycdQ1W~alc-uuVy7ONsOuj=+=q)M`|mtj+gJxC#%osDp|ULe(T7zN#J>Wj#dgt17#rW6ZpjjF>lM6d^7M_f'
        'mOHy6Es~-Cs!pKGIct-'
        '7dp}IVI`KgL3LPiue&NxNwzN)#vsZ#5GXp(~NZV8}Tp89sdT;x+_$Nuy=43U~0GTa~oBqtjzwjz~r>sSDe<L6MnD23w;fQT*bN3#'
        '%FZ2O$z6Od2@j$P~maj%A%c;494)2AU4;Bmv8``-a1;5MXSk~J=mzxeT=p4l^3G2e(kj;fy&~d(a?23JVgv-'
        'R6GENC#)yQ1q*nu(8<<{3WPCl}9eov#n-'
        'hb3R;Ao(vhs+A0WlBw`N%K_eKR>YJPo`;ObrNSfQ&+Og^Ss5v)2z#E6`R=&vzE?EG!I~_>P~UVRrHCl4f+}mns$*4B+=Yqs23n1_'
        '+tv24@y@4v)@OHZc_gGaIF8i|I5##2g3~!3iW;Ct(_uS)1+tczi}~f*ms9ChV^LCdDzh!B)cjI^<e~i0+Oyp250ubX4MMHjY4Yr$'
        'ijJ-LB)O`4zx@cjK?)?YzJ#j^LiP>5EWZRR-g{X$yJW3Kv6LWk@VyCFUDcPYNACQ^9v4?_e-'
        '0|z`DZ+M)Ux(4%4xq27eL5bJN5XKKf24=aN8~v`<CWNiaqVU9l_r0G?$M-'
        '`fIzs2|0E#wtAA$MG(PEm#@WgXz#yM!&Wv8)nnypK|zh^=TIxzVqNKk-ZXwsp3tGf^S#eCRh_BE}(SpgDI50twZQXv0k`W<iZ`>('
        ';&o%PCw{#9?NM61dfm+)NsahU3ZeGao)MS)9U(C`rX8ye)k$n#}*WhZlV$~CBKwLw^%(AP(S9Bq`R9S$QC$Spx0lfGkNCV`;XOvw'
        'g{nTzih|ScJSdehr4mZp;3cERf5cAihAIS$?@H~M;&>R>}Xwya_p2^uO5O&3Kp77QQY>2t*gaNd{pG;wB3oNry9Wi|M{u(N-'
        '~ls9^7iz{)2s(FTk{zmUG~jZ$=Yn7bwVv$<*M5=yV$*^hmm~Q`_hl$j;p4hu04r$Y&?$CM(h&x@2;vP-'
        'C+%9OC$FMn*eH&rDoh=mHK7)RxvNtk;uuH$L2^8=!stLKNtu6Nge|vc!>g!4SOYFR^K3-cDHF?+885M-'
        '&sbYQ;VvYHeK8qk^j~YkxM0P&dsgJe{>K*7?Gp%7w3{U_X$Tewq?$2bU~~&!n&@MAZ7AsmnRVTsUBgT!RRL&#ZInqBaxe;9#)9F?'
        '@Y*-zWTze2!1x5|8^b{5aL>6UYW(F}9$V+x@-PDuRjau#+SK`nT(Znp|-C$NL3S>`%-'
        'srb84<OX$rg(^20RG3N2`uCE5Q!Q}Ou7%*nZ%p2gQ*oW0kDylL;3Cw<O$~>1Ez{xux#cP2x$QO8W-'
        'dZ4!oX`i314Ss8;GkrOkF^u$u<P+cr!^1OEMqobAl^vT>9pMia0b=PqS!I%b5{ShwD1GIiG|DA_}Z+28=k1|vY72C*~KF4kTo1Od'
        'dxSo8L_?L{6vna-'
        'M(~kjbq#|Km>1sI4EH=&5!|5Fwu5I&?m3JDArIfI)4pDgw@wV8STV>BCm$O{KWU!3W7c2`optejW^;slA9Vs#BAV{>R!m)J+(r8*'
        'Z<}|o+^_7QV>y#>>mJ9cs8|@s<AHU&1VQWSc-_XVHvn6B3$elOZ{v1_M?+Xt9~J09Oz;im*$RG-RKv|R?)y{8xPVyn(70#tseM$o'
        '2buT&e}|NaiVcdL@XF;O3S!4by!dZFxO!JR6#+|e2oJP3h;Q%rCIRx9~CS<&~97zJPFNoXZsfIb2v>AgszBVAX=H-'
        '{~imyGO>^_Dj7zkwKejrFFXd;L36F<#G_i+Bit!0_p0^JdcPr^+Bj=@{^xfV7<Iq(IOzbE-'
        '(TE7{Eo<Dhv(}g9+*Y=Fn~?pc+M2pF_NYcOO>)V_pb)pG%b@SkTqZWLbWXpY=F(WdWjc|0%r$GMei}OBTC+=2&Qbbcb!lBbO_}4D'
        'ZIzm6L=4VP$iS*$6n~7;tS!tdmGN)ToNJBeG?>^4MU>BO>QA>r_1GCe(Bv)f*&D&3>V6ANHV0vh<kIQhhVRq9{uIXVeg%|_r?)C3'
        'MLmp-{E*HN#^khpkY;?1X9zJtX@-C<}I%ecT93FNi2`ud$lC-)GNjBW4#PUidG-}i0WdfCR%W~nRVNmnKIg1T6euvt-UAG06e|rn'
        'IvIGeHUE;pb&L78NJ_v$xOVlz5)~1Y#r_LG*8!yKVxPbmnCAz@8YSPUa1jjvcO$Mpkx_=>z4Q_cH4V<uW8sD^IBd%?`iYg?SrT=D'
        'IvZ00465UGyZnkCyCq`(HHoO$<(XgQZxVfE}M{N+!CeN?e<{C{^bUL!?v8(|L7giT&z$>7IKQm{*f$D`DRbnyQC7|=gxEq`a<*`7'
        '^Mk36w8{Nxvs@%*j5~~FaMp;stRGu$C7-'
        ';PQlOgpz~nHjd2w2Uh$Q`0;PaYSttZN%cE;$``t5+nrKe=ily?eBK?vPMVoyJn2(}kYtEM}la_<jZ4gjGr4*P0#Oe6Y@;nX)NwJm'
        'W<pS?dG<_O~ET^dPmk0R@&AQ(($tK*z?)T)hP<}p57}WK8bN*?%&(c=HcM@lF4YWxHX_zbFN>orB3qG2Fp3nWUZ_<6Du1bEaxRgp'
        'qJ17nZy}k_*fe|E~_fvN>UibqBWeg=;ir_vdk1_!AR8>1&7SI)y(Bi{N^DpqxSy(!xqX~944SHBw|Gtl$*AMO`11x{hGBF^dBxZr'
        '~^Khf>GUJP%i+?uZEHJh|AF!s{c{R*|vIh5DbGDF7)s)sZO}V+WB#jK0Nz|Xdg6Q}{0bPD8gNj23CfS?u1D@bZ>?e|VO>K}LL}WZ'
        '?sPj{tXp&<!xBpmnY~Yaw`=4!Rt#HR!J@$a=Bz+0t&u(asE-'
        '+?*Pjk@CRA}(q=K#VjfXd$)=cufA7jyhwJuz%qzfkQ$F#up7gMBiJaUn5V&W(y>?MiU-N^!GJVa#fL|8E?(%V>iz9ZDE4WBi-bi}'
        'yw*lUq=WB<z82!Qu=QISrtrf~+RDi12}f?biLvdu**qoGHdz<_zcxd;nJizVH@5%zy?l3ZDn14CDc%Y>c1+Vb>z*yFJ1MLR3>FW%'
        'IDl`Tzg`000'
    ),
    'mipmap-xxxhdpi/ic_launcher.webp': (
        'Qb|TeHWUB=S4BclR!}%t3IG5A5C8xGzW@Ng002QuP)Lvi0004?Bklj%#`}Er{V6=-'
        'a_Kb8uKrjpRB4^b0ep$&b+0=tsmt&Q7`9KfApPJ|nC<bmT8M}Vz_>-!Ii1<gsR*W7)WLvGWm;4LpmF`#<4*axoWY;V&f{m-'
        '8vvj>1)>5h-g~=w!5M$C`S#u-'
        'AS#n34#3@)$0V7&4>Q~QM3ToZ?*ec#K?<y_Z;}i?B+mF0d?2~Gz5?i^NQOr1fQ&xUh|x##pw&Po6QMx!l=Ok744yn~0y+UXF1;sx'
        'q&cG}-(NyLF3IrMK0~BQW8nT@$Yd-cXp^31^<*0&V~`95L!@D2V1Z0VCMpFh8n<F0DkG8%1#6nOW`RsbB7%Z74P3K;$Ot5#D_GOS'
        'HH*1ihRe}rMI%>iBOgl9tm<T?R98*t5RzRxVWgQOPp)M$m_tcVLwlBR11TOd(A0qsp#z94eM!+)F@0GQ>F3a*r?EX-aD7CU&r`Hk'
        'Oy|oYy&Tr)X>QLoxL%4q273kWL3=1}rbvUwbQ9X;@Q$^`YQBT(!opcf7E9@D0RR;DQlQC0x(5Xup3~dR^En(OTij-'
        '}S>*O&CW57}Og2mWx&%?&_z`II@Z$#5VU^x$o~v*U|6A^VI7NrSYJnZ7V#9J9U7sxXsjIYH`Nw~M{P)LyfBg5ye?O7=WVugW8<yM'
        'X>R7G=b@-p&YM%eYIjmZ46;5&EN3dG>aRVw?`pRUp#IH*b$riU6Z5Fw`m<b%7)7#ARIUJz4mx9egx(5Y-'
        'g|n0_meSb*x*guJwph(~a9xU<DOxP1o6s&O_89CHxCcc~hc$Y8d9K0r5?MY^(ONN`FN^eoLyO*8o-'
        'H`^6<PX{qOD^3vLw<EiiZrg3VaB~pbjOyr94YG3@q8T6Gl5lo?OdhFesW;ovf7VstLugIohnORI!a5LrXqau(nanVlJ2AAcBImg='
        '!WM!6+p|!P-7G3uJ=Pib}!CIu#31!Kfue!4NGI0}Et=(Tku>db@bC4H1k}GW@mA5N#3z_y0mB7;}zG?@1r+5k2|-'
        '5^{`Rf#xacgDrw5Pn&>Z5+y^UbwEZRtq^@A4_Xamf(cb%Wqp%m@FC5*6nr4LxxNA@CRZGQyDyJPGI<|nw)cr7k6+#e-'
        '~<ybD!}5sx0@H7@fVwK?=1qNg2`6}fX4M_k2~e(at41cJCC1TZvcQQrc~6yfKCO|ETYco%yv#iFm6^*I3R!!001yb0G$CUzyQDiJ'
        '{byxL7@bu$%O;}VJuDG3+W(7dNEbrZGdHzk^jE@An)m&eP8)M$gj!Hu8xlGukM%kAHuAgFgKj1F@JjeU;g3$|NsBspGIC_-=ja-z'
        'be1LcU|)V`o;d^{s+95{14a<bD!INKtG#*QuU<uKmO(aJJ>(=qtfI4fA!CUkJ=CWpX<H@|C)bv|HteB=mFHP)gSDAvj1V|>GS8Rz'
        'q)+>I!m+r-'
        'T$wC*Zx_1O!zCn3)O$){~kXoxZ6Mn<R8)h+kRkwN#_&91Nl$%@Af~KzXbQi{fGWnum|%G>fi1EzWzXcGXFpSJN$R%KeZ3f|H^;d|'
        '3&Z#{EPZe`+x6WydS^+RsOlZXg!jDSby~v>aZpjmzSNl)WC9?b?|4|ryVm@T4w+nRs6?X{&$F2USd@Far5Hb|9}=9Kv7fo2e`|o0'
        'A=tbveBj~D)S2}L`j@04^x5^goq;O^3knsg3naC-i+1J)mH-'
        '5g1&|1Kv~17iteEsOg}dKr;yOqb*`qGg(r^0Z~)X`CKQ!`Kp5xu%-'
        'iYFJ;BLGk2fo3;cE_CeR9DfMG}1&JQ14nr_hiZ{9Ak{Idokkr(G@}5rTSKxA|piX5k3;y#MXX1Y8?T<K6yQTA8^I{hTX=3?MidkO'
        'FU`n{lF~-g12Q+?-'
        ';;b3N^7{vo5FL!)zwRU<k`+<0t?U?7}pXq$?gKsfLY8r16?HmvapgwU`n+}Y?X^LW&bKiwk)Puc3bq5>yVRvA=i@nXr;6uH)MDO{'
        '9_jBJ<a54cT$0RI2+Y=l`I0WEO*fR6NKq0z0K4(OcySXef>JdF@dnl+v?4SQ)QjV@d1*#?Q~MK-Lxf%*E0!V+SO-<I}CwI){4)-'
        '`ENylgjWy_Ze=r;jz($^Y&PkX_By&QTwlC09;v=O}8wAx||}_=HYxi_XjQaLf_17+a3@5F*EtA74|_Dh_u@<LvG%ZA7O7g)0ILns'
        '27(v)ePx#bv~8pVXU_E%2PoTmK+T^Q;Yu{5oraxyegXIqZK|jfz{+0d1Y!R^g&rV0F*eht`;uoIE_Er$IW}16!S>pu`qo+#awP_C'
        '?5qvMc}Ggz!7^KmOK=pFfVOzN?YQ%{plD!D%zH&q}R<Hmq6G3)F2|i^X`C9Z5`C`bE^16Wc8`%W0W|`%(Bh^p|=SSI~K~?c!s*)B'
        'WhCXuflywqY?TrrzH-BvlY^@<NEZ`I$sY2R*3e4pOn9dor?iDbIKZsDR*1tf)N{Hv0-<aM;4^c2R7QxOjE8Sl_QXd;3?7`duZ|`-'
        '8a)n+znLPIYR2&NUED5M70U3<`RCUX2Z-'
        '*|cd%V=r~$BKMBRoYXu@kY)0%Edo8aQ(r{6<Uk$XD*BfO0A7~54doL5!>p=Z#;|DoJOB2`R~8n<+A>GV8*h#5xzIsNpl6La+67BP'
        'w!apjxK2@v`+DL)g&IR?@h@=+$P^MN=vx!&H$|CAJfJxY*^AtrPz2&;DgHt<R|_i=b+y7Lw3wJ!!@ZX<bl~?9K^5<%MJq3=oxlWk'
        'dG(Z}iKby<*IlPr(}d^=T8D5FQy~R0EmBvAW~~5z>l+S0$re}>J0kK0hI5t3l>`}iKwF4yKs-BNXZv~k?Z{YP|2F<i=th}S9);Lw'
        'LC;MIXr2coHuwM#&S-kR*~>E0xwqt1*7TZC-'
        '<23FaQr7qhrC9FDce+)Ac1~6@_;1Ok7rb&9Aay4WQ?MxC3@k^Xvs?FE~@AqJx{gV2x;O4HcCoPP(W&4hjJRYkv9h$RyXG(>3=L7v'
        'es00OT2*#UuP2x<fw(#9jOzl&68!C8=!FM)<L<nRFb(vW0TXO&HPBrl!jOFp28O&7Y^I}FKXvGdazliptOEo?9dUQjkD)^XyBH4@'
        '*#@3bQ1`)!K?L(N%L^WTD+o^O~#%n!KE_$gAP<J*G>8c-Y8w^j&+*67B{EzMaN@ey6j;uowimfkf%{skKElfXMs{Y>ij_3k=)-'
        'xB+jdQm*KpMd*~Wp`@mnxG%kT{N~2)@_coEkWj+!-'
        'nGkz{x}9f;Z2lCZpzB#(pL)MZVj?j5kMltY+GV|Q@5lK&obTN7Ir8=^lH`W|_D9y;+hNTAA+_2*0IXRw6OCLC4C*S5C$;P5r%vPk'
        'MxGAru03f`5A1W0A8wT(b}BUk8dX7`;)BzOdK1GyiNo7n4dSRF+k;eHNn=6AGtiSqFBTj{5#r3=?tR_tq<Kdn%{J=A)48X}4QC2x'
        'zCLp@q{VPqTesn4Gm>2A|H^3H*<4vAg53;*;D)14RnOcW-rpnj^dyJnKKeUeV#71F-'
        '&tu!ydOL}$_#umhZ!*;Nusi`#)D;86QrJpAb`3nWOF|UoW)MQ(^bJJack9|223R>Pn23Szy28@y2%zlJk2;^RX*Eeel3qw*ZnZF{'
        'yXkQT`6qeO7)B`aEgXv#b^tCgSo4GM#pEOA@HJdt<nbFdD|Nf0E`-'
        '`g?v2RMfgvOavI>v3=1MM*lsb6@^x)c{OnSbq5C0v@NVf(j!$^=ezL}SKnK{Dg?!PK>_xCH60#}uKxvaoEV9;#%X6`I5u080p5eU'
        '0cJa#d2cb>8JedZ42+T;ED)OWE>1-6v`l&yOorus&>Rb~3KNQ-'
        'K2c?+#rB!*dmKGKj4gden!Ls#9WJD{QnbWH)mRqJDxcUWXpEN0YGsAulHK&Y7=@~`7U|B=b-'
        'Z{#xH4_Q&0rVw>n=9@WwcqBhZmj(3TYL8HmwcjgBf`W+pl;x2?v~A`IXbXhUI4Dm2BapE%6)?1lOe2m#q|o9H&@E0ewGfhPNb;KD'
        '<y!a6NfKkTJ}k_^%^p3$_7s)o2U3hNOihbzVCBSGA-'
        '1oWv3dZRR}fc`h8AE%JaqHKE>}_tgU~6t?b=4A|>~E&yH{<Qhkm}Qt~%jw1=k@S!6*LDOUU9X8SJd^Z&E4<CHmyueVC2ZG)7R6JP'
        'Tfo&oV~FUr#DZ9EJAa|Q~|GqLmnaO6nu5Jxt@r5PbLogZzzxXeh3;|6>&i8j=4o^op<B}2#Vkl$p`e+UR;0t@id0$oY9pnse)p8Z'
        'O`01#L|My+=b3?#-'
        '%zDc`mnIq1TcaclfJUvPsiHWr(^Gb5K{?+sgvAy9E9K8@C8<PLadx<mka*V54<W;e<|2(Co!$HlN&&An2Y|Xvxj~BXCCRznEM3I>'
        'M!TwGu@19ZRVViHjjF`H|>M`KqDrRVxa^SV+*Yb)MReXKk=hE<lw4slt$YTqOhJ*YyqQ}vAC8uTdKf)cX<j1?HyWF^QZm%rNdUCX'
        '^yVmrNPfgz_2rwd&p?**s8=c8enJp>h((FBZ+x=x5cJ#kp4f;#ziKrc=nOfSnYK)Gklv=6OwlDF49tiBrVDM85HF@bu`+bBWOm3C'
        '5lNCnL_q}|PXu1)-<tQAF8{fEU8i=MTZoN>8C%u;wg5Xungl2y%Ew8dPU$Eult)zSP`WrEJ<W2|w08cyyDiW}f``GM-zZn3%Nb)t'
        'KqpOZ*Ocy*ZZ3MNJB&W&Ae}(4raG0yHntZTG*z#AQFrT8(+b_5@>PQ!DD)stKEYSqAQwHYZ$!}wWd+qJKk%#INWAVrR!Tadesfph'
        'kfL1@-'
        'a$fc`pnPfyP&|UG(4o4dDl@W1ZxD`d**|fh_#hDPM(vl~R6(PnW@Iww(c*;YuiOZ@#a~dTpH^L%9<z=NzuWB!_x(q?X$UGv1!K*Y'
        '(!`8%_@@YW`sym(hN1QZM+Sn~(qb`Q%04K43U`|SHF)?+5J^Z9uO<+Vj};aE*FrViSpgR*pZvkBcYs`$0Q<eHWLv`*a@WLo<bdni'
        'Iny@hxA@G}tiJGhjCs-jq5aaehUapc8r=8_M~3dW$V1uHhD5I@#2h)o#eOUB_NrDP@BOdcWSY^u{-'
        'jHC7(dw_sdmZZxYZj}(C7%t!c247_GYnPP@N{DFWN3FIX=9-E(?~ZcaawquC|rP{i}GJ9vSBx>;PYltm-'
        '57_m%N8<HzHs4kF?P^&k$36GfNgbo!cwTC@0PeR>w2l+E2OMc6d`L4mb)-'
        'x)Qm`@!u6DMQ_&bahCxdpm3nLekZ8kK>_USq}^6g`?d8j1Jz<pO79_%Lzg?V3nlmCCy#P?{iToR%a7&L(El^prK1Bc94eGR3)-'
        '0i9y|~d9*FQ1f71mq4YOQOYs#vNH%Y7p}OG%Nr%z=K3~t~zSAIi2T*dRlHUm=AB<;j*;8JGp`0#DwsKc!$)no?>mdXMSQgZnSP^T'
        'M)RF%(CuHVNCBoWStyFX%6RO7)Y9J0fvrA^9t@@nzA|VKCee)L%QvBhGD@x{iGDmzq*&9Dxk~yrCp0o#9PX-'
        '%L+eR_Xfs%Xh;g`?)iO0ilRoemWqXFvmoCP{ngd!Zt8XZlwZO){M!3>a6sBSyTidgwheY#q6Etvz|xG8MfBpgw)ja=H#jDMHF&Tk'
        'YR{5ft?399-'
        'jh#71GK2uM`Ztj8kM5j)uuK45Z(cF~GT;<eya&HgvDF`mYu_1=JsfJwk^pqmvgJ1x=wb_<Q+sSeMk$n}RR5AUTAF(Egb=3C>om`N'
        'g5GPV=n5A~sV&n>9Xl;QiTBsDG;sH6A`P(1knB8c8JJ;L$+gAq4gkiL&4*2oSpa3fYB`vnSKmxnQ566H+Rh7^NF_RCKJYB?W_BKX'
        '=CNy95qwfZ=v5bZUuZ`XY%jdp@(0elb(b{V8J@iMmd?dm^c;1ult*EPDJ*NqkWi`NarM7K5x>2EC!>dp`KmI<-F25y&;NDr-'
        'C@{PI>Wr?Ka0`dCIdW6%c~;!gDS*}Z;kLZGc0{tCVtEz5&@vNINe(60xREU^bUTQ$9uYE?ADh6{U$IlQzi4O6vM;EnX{5~ZzJJ#k'
        'eS|i{@zu4n?1mrm-Jg+HE^Vt<jizOJRe4f<=<QQBEr?>0C@^}h)cXI~w~;yWKi12Z>-'
        'Mm|W@M7C8P=>Uh98B>lUSs`^^FOlXgWau{sD2oKayv4r~$veS%Y{KJYH@3{2>t7(j>6ly{q|FB-N_Ov9!;3(<t)7na=!d5<*HXq|'
        'Qh1%C#^_DXfEie$)?yI{nyt_SDGi*_^@77g`ov06&rMOy*qTF1<4`wvU)a<WDp<Om=zScfYLaeW-vVUtzKNlmJUJkccG<qFL7zk8'
        'fepNRjDC{Ut2kmT9Omv^eC9fa9%e*gefuXly&G#7=Sh(Jy;2CLZQt=Ev8U6H;&*?}boc=(aJ2QO_U*3=A~1d*gm9%8nFX-HsxNLo'
        'RwqNdV+=GZf}6dQzsp%IH<L6S$olPVyp0hNEYhw}@>EFn;aKzK{uLIipxDYp3d?fcgbot;wN;8+YG4kox=^Pe2)V1A3q!Bxlh%KY'
        'xjeiYWj&cL~9|uUUk~;QiKRz+!@_a2^rCx=LBGED(<3-'
        'z?|Y9N(`m5==dPrV&?fduSyWyGS*6My3R}ztQaFS;$(F*VjC*1(g7Ra)CNNv_ZWege|zP&fic!er(^(C81)^uk=SaM@c5*Nnw=BL'
        '|q`?pRWs`000'
    ),
    'mipmap-xxxhdpi/ic_launcher_round.webp': (
        'Qb|Te7#siqS4BclR!}%t3IG5A5C8xGzW@Ng002QuP)KYD00057hHaZ6N!I(t_th9{+qP}nw!J;aw$EAHwvE}IwfERqTVvE05$}&y'
        'Av6A-h?oFWuLLvGmYSK0plE}d3EFL@S|&ja{f=MssH4v4ZQ;b;bB;KA!|@}~S1m|Uh-v_UrMLdhwNFl-'
        '#&%Br&$U<Vup#=YiIjn;0>HBS{OnIt*{{3DmbyFp|L1jQuQ&_<EYzNa0ATKI&UxBNGDeR%vyC|?_n1lY@An=$9{{M-'
        'Sx^8A9el?ZB$+&Ac4~4b$;mH%XB_~lb)^Q3*!<2<NoJ3kot|POnO;3|VL(*sM=Su#p7S@7F=lpYPLbpn_ih8gLcNFr*x|-'
        '$WR98Log&GJXU_#_s1Gq<+{urS^u!9xF_UlobTvRjO(-'
        'yS!kc9F%&Lr$oPEXWfJqI6fKg}thm4Vxnw<2jR|2%^#DE>2BR#Qlvy)TL7>f`p&46VdCq1*8oqY2Uz@)N7G3+<fm=Y^HJ2`O;Kr2'
        'dtL;p-'
        'hR(eXDdfr&5RFDKLcsuEtRUgT}Zx4jZ3BdjzGbYwxcJjP=VHKko^II~qCR5^HSA$5ED3<vnJ+nR|=Nt?Pl@SyNO=D!Orp%j%!74('
        '5Ysko&&6$5$8CD5~<?dw4tY7Dcd%-'
        'H8fmJ`Evz8OtgNAgQVdW3#tm)Kb4<Oyuz!{%2vbJ;L?V}O8sev9cvCf^nBN4jC&_hqG_c@$23ZYvX=%HuUy>rrNgzhl(&@=1b**g'
        '-U8w@@4%o1#}cT|whYv5#hW*Iss1(QxwtU5I&mSU4%N29|6R{nsA#h9Dyfpt`nB|c<iNjgu4b&xc|{d5*(ic?pGc8=m2Itw%Lg9Q'
        '*eMR5?DEKcX04U^6YSbR>-<-'
        'sN=pwST$M*NkDCED~IV4a{ihml2^_|Jt!+Nao$O%|&20a)84%==l)rNSnUgtg0X2P2C$=c$W^&>q7fbQWyngJ@H*f8<y)bZ!l8hv'
        '7GL7H!IJjt<hgfTgCVTsCx0fVIx#DMprV@|85SO0gv)i`RKAtVN=uUdjcO<E%{)T4Oki&H|47qiRbejCnVu5~6btXe$h7&{@QhuU'
        'lw=gt^{hDkDbjEjF|Uj;FJf@(Tz<3wR>OQev9EJi<^E+cC13o!18)is2S|IpsWkE|I|nS?tT4%ZZ*&hYil~J30$G@x5^(g9@Yn%T'
        '!WK+(B$GDjPGisGIpR3=Vf?FRPrtTof{pV7||DE-'
        'N~ZhYe&nl+MDA`7zOf)b7p2mGg|nA^izPf5BW@^n8d|e~L}!M3xsX#sG#3=;f99{yZZ6sJ+BkUL@B-=o7H`9F}-'
        '9_n^_oun%L2Iq!n@X~=KbEV0CQhN1u8GnE*lZvX`Xmiav8GUJ3kiY*yg<j(70fZ@B@%PjGaqeWo2j)j&vV-'
        'y5o*prNfmZz_QAQ(G?xy<N17A9D9N-nq4VTPmWEcD1pP{ZLR*W2fe!c$CQEWF<T`(k48y-'
        '<AT(2LG+V98DFb5hB@01eo1R?5Y84pcB|8cWT2I80>hf0zm_`tDE|uBMk+=9JM87_KO{Psc-'
        '`*qO1+oVSVriVbF$T0R$szHc%WS>z5-'
        '0E!#wC6@Ci3qb%haB42H$d@1h5U>i1yqSM0jXn~_{gbJ{5_f|3f#NR40^_VjApMvelDxbk9}z{rg864M7nk!?Sbqq^-'
        'e4@Q6gPwpVE7ijv=aYj0RslCIxCfy^QW+ZAoxR$g_XD-!XQkJVqrx-DFK5NSzrotQ8|xAV=z$MPcJI^5|ANmlT%4KuNA}K70)sjR'
        'Pq%OhF~~@UQUs(Tfh)SM*TOZa*BIGhk^!v!e%L@{6DlX$m*U;$@xRr&|tWhUPd{8F`q~af~+t*<|1-'
        '_ABI*MuA`Sw&R@(c(vl!6OpdvLoZo<=wT3h3<rCAZ2xzhBxR062hkL?W1;ze3mQLh-rf9w58OE~7F)fSGh9E0XiMePZzXwA*4d>E'
        'JCZ+d=i?l^-'
        '{C`s_n8;nBXs=>xdbv2Sf}!1p3+bhj_||+Ov`uvEpK>ab+?=yJ6zx~6z?h4q$?v0qPBa|CSR#@44{JzAKyeejJW_mbNd$DJDE`4%'
        '8aZ++C^|LB>L0{Z7)|!T(7A@)=(#AGyaR?#HuNy&f{5%LYtm6r^sreDkxz|;pu-!ulg&~{oVhR*oh~-'
        'Em(4OroUtVooi7;KOD}=M>03h4jRB)4(d#d9=2kFtXTYdQY}Q@kj4jbXw+4*trPo{J^etiN-hk1)jCB?{Wh)rEIiT@XdaA8CoU{Z'
        'K-7SJ1GS!r`cO(?uE)AUVIlYcj;_aiMs6fLi@3UDyk?a8km1tP}R;E-'
        'lO@6dJR8Wx$Od!2ZQskY>!BCwcVAsF0nQOzz?*oQPZD65$$XE|4^56SH11eU5V<t1D8i?ej3!;JQ6~z({ke(|pl5g)0C@R^2?f*-'
        '9uCNs8-x-e}sOS(dX2KjYRaK7UoofJ!3RhsY>za(Iin5c>?+d7)(#3$SUnFD76_X<Q(Ki7JsQjS7-'
        'Y=7kxjJ%8<cB|A5TdBXAdr2ZnMKA_4LOqh_xI-o47I5MR=R33nLKx0jHJJGfB`0`Qx#x=32%~&F?UZ+p2-'
        '=PuMR*3bsH2IyVJ!}NP0}&kfW32qbDx~KvB!00G2-PfoUY^F?CW-'
        'o=EbKzt{+X20>kmDuBh0y5dceOwm)$ZOhp`lH{yMj@wXyU;*_WGyoX0`Zw?V5BqhGZFEoU``N2M*l`H}FhvOlQvk5d&c61Klb!9J'
        '{OL{SZM`4>sHvbBC0GCe8^8Kdr}wseV(;&c+I{>u01(rF;uKXwN1CaiSVe-Fw$V&QP_b4}I3R`-'
        '003}S0G$CUzyQDiJ{byxL7@bSqlp9nVJt^)o#ZqiS`?rf-^uflzu0~z_sGvaRsDbEN9`ZQ?SuPw-'
        '!I$W^*?~u^L}5H{>%O^@sIjn|Ns8qf&bY0qw@v*F#gl|Fa2l#|IOE{k1)T?zp($+|5fi1{)_e>-6x<2@=xquwO*#b+&|s>0)H|7-'
        'T$N3@BQcbzk@&8pZfpqKYadzKa_uH|Ec-c@&V`p>J|J0)t{-~&pTiLANfK10o)7huULO-'
        'x*YD)$v@fe$^T#dkNwpDKll&$KK6J4emVTV{8#la*<Z=tGQB(fH=q}&|3v>&`Gfuw)Avz-'
        '1p5GgF#fCli}JVPulAk|A4&gT>;e3@`bYb}@gKB*;65}z%KtU_t?gU$ukru(|IGXW{~Z2{{^$Fz?(h14|Nm9~wm)Zmi2qx^>NO%e'
        ';;0eBqPC-mPe|NcI7VHHTWWiZlG$pTm>TlyWc|O0VO7r(E&`XYj%$pbG`E*Vy`>i)%s52_zmw1MD58QJQ=ls10*pR>%NiLO@n-'
        'Ko$6U`_r!+tQ+HYDiL$hv~X9UdAJDgNQ+izU(E*HtP0Pa4xv%mUWqd4l@BCwv?csiY2%AWZ!=Lr*>yhi)Tj7yof)17ip)i8bNuHn'
        'q`BVZpduv){FGKw>jO3g+)^s)nz{B3>S8#@xv+riFVAuSgzQP2^BdRw<FwULU#%6kPfMDLG<81&@zur&M4eo(~%U?6WIe_IM)sZ@'
        ')Ws%>ah@@lH@#lA8A*7vF0WLmGK>Ba|J-@)VA4y3x&eQpOOAYx795*(wATUWqRG5Kx0nt6u|7{-'
        '5WS<tmx>qlo9s!M)nfcO@3u959r$mWN=y(@;hP@)zC!@V?rwr$i$FP*0r*WCGYa28#C&3+cn&&!P7UYatQ*d;2k;=lm@|GNK9y!D'
        'cvxw2O>^J3@j#ea8(J|`|LH6aI6LEc0lBRe<MD-'
        '+x3ECK`a$7=~7a;+tT0@WV8#gTVSqtaYn#491W2Q;U}ulTksQ%fu!Icd~>s|PBsD{Z+h@w3R_n1p80hBOW*v!M^IufW3XFrDi)?e'
        '&?(33MdX`X6Z_Q(BIw6mh@D{KSW{*cZY2Qt9`>rLOV@(efRlfUO2kpV)!m*JksUdCykobie>j$1iQuET25rG~~;RQrJpw4e!5UAW'
        'Ery4(@PT;)y@sg>YR(Uve`f$#uW3QI5VFQjQ?@A>#ij-fVB5POeqEXa9X_FM{HK_?{REEqcTkqZrmgJW(umd;P6FjrwX@FZnD7Zs'
        ';Roo>e=L#_FXS<6wj(ye2H5`ieqxM>5=ycINJS%<nhA93TF@Oify+!zKA`wZ!l?K+f3SMW=YP;hiTZp?(Yn@qmGC0*|8EZ#KW=^q'
        '>F2u)34^s<y=FQI9vtQOX9`eaBzVtTRCXg=l;K>qjU$nC>ez+A1ZEFn;k9+l>jd)@?;fXJGuv+$kr)z4=tS%)gfrY^KQxt_Tb(&I'
        '_r*H>@oZ^imJ{H7*n3^FLgU9mAd{hd{MI&TPNQ#<Nw+2AfUb81=Sd8<Okx_zixccUS2oYXOkHCr?un8Ln~8a#za2aj2l342B$#+^'
        'ytf#*w~cY}rqY=tlEo3G}(DNQj7(jU=Frn5eKe;NTZsk@VH)MD_5Cg2?~+jBvG)CuE#jJQjBf?xb|{GCrh}%buoCpXPP($_SbuJ~'
        '7Rj)?o-gv8_a*o4L0j0=DrzQy+v^dig-M_|t2v|1n{k5T!_$Y%EPMQZ2NmmQw7)1IWUF_h;VZX&{xmg9>AJ?!WRWWD8{#JK;~27v'
        'b!1j`Y{DWsB7oRpufDhsLBA5AfU@-'
        'P9Tjl?CyR_FsYVH0Zdsa{3?3oSJ>$@><fr^Oz~Lm#Yt<cD1ngyg%c7iB)qw2+ptnETS>PXyrn0?7~BGN!}*3g`NXh&;Qi_|C9T2>'
        '|R5l2yOi|<CuVs1n5G#p++}w3ISo$;DsTc<{1%y+d(B3Hyc)t_EB&LPiry1@lyY<bqzNJJr2_gw$LOOSo*`lfmf<#vhy!yXFU{h&'
        'l?Tq-^gQpa6w^)ub@zu1?{-'
        '!+0~QQxTs<T1D7;x0=#U>UBI!^x=ySv0Er>66Hq(5jZtP^`gSzg4{7n?lB?fisG@$2k1B$95QR0L{kz|*T*9eff}%NXI|SAJnXi}'
        'Upw0h%F|eQuig0T8zD7W_>!@sYCJ5n#2c03^$%?QxjQ*u^YVz2Prd;IXLKU^VKcqxRd_}jne*9psV|{lVpiZYeaXYOX;)4vmwgc}'
        'yUNfx;sh+sd<IP+&Xoq?rDo%gALd@dQ818te1QduF6ZACf-'
        '&v~d7W4PxT=dT{X;D(|l;FgOi1BFyo#&IU?>vkqEG&@_cwqITKhD_F2PLX5Fd)L8i%ur{lU`K*VTP1I)j#SF<<SHRJYqSCPXJR;#'
        '>1P|u&ui}+dTG_L<WCKcU-sys5uNlA3PNLB7m&TqK}33Dyz@T-'
        '?cT%m|2ioplc~Igcz#_(3w17SYkNUKA~__*+0xfz;K}^@8&?s9}vfEs0Cs0?!GwIKj||KBa^YDU(kPhK&-'
        '3dsAxnswD!l+iCha^S8<Y#C8A<m1S@Df(W5qt(BeW&Ad)}zkDGVetF{viYS9qJu7gc@_7AOf?IijFzu|;E<#X`qipz(%uLE~ezg-'
        'Of$9%>Z$Axm)q?MNzGV__!5dxc}c^z*QE<|-rW5)qHH{sNpFl%$XZuDUv=>mv7-'
        '3fI}WO|XgWo0Ekl!Z}i<BkpvDUFNZDH#E4(7h=b+Ej9pn71ppB#+U7V{yWVxwdL8-'
        'eSM(vi17biFF+umdsTA0K#(G4Glc=PXGuoN`ZKq)@4X@yOw_~$L7#ARV4R$e~~kL<3ZKoa6T))4Ge5d`olJbz)>9ONqy2xh44nZ('
        'JrowL%sIdenaq&p#meAl<Nb7T<{r!cG|ZHj5+4&h)liB{P;i}b~!}GXdp*B=cSh$S^C)s0nz7I48l^8YGYBL8h_h#hEB<P-'
        'E8lbmLYJ_8FR!+TKcm@?S=g7%y|z}|N77x@i%!##2`jZU?US0R%X{od_oiWQ60o#Vm{>W1PPY~f6t%xbsRBQAT;P|0nP`p6q=&kT'
        '%x|@5GE73a5oZA7nDA)^qp!Gw(SmKJZ|y7;P^436so*|DTUk-'
        'c)7kvZI{6&PH?HfNIV92U<~fI1KYH?Bbe0kZ;TDOex;Knh?jj*2;>EE(RaZJWfdbI9sDM)bvX5#TYJ$*tbbq}B8A`w=Xoe9Ygh~`'
        'AP3OX6uNWB*QGOxTEXBBL|BU$x+LacXDu+!kx>vjHG)m?5AxMsPUY*Cj%=OfAcNSyze2_f+m~<@od$G7Bc;jqU^|y+X77AHRg%nw'
        'oj%Ew=XP4Lwf?hq8CIN$dvF}O=UM5Ty+7tJrZiTxhJJa!+Da?wCIS!#TFLG=vHjL1@QNY;UUNc?jfAV4TWD8%Z^J8|`dQ={BOU$7'
        'I5QdixoT5>m_Qki1+H7}gi0`R56yLVadST5HXLT`{&=XP^l?apKhm2-'
        'S0Q%l$Dlob8kHJIUQq`hIe7b}V)f?p)GQB@>%?2cH93Qx5PfIO*0#v1&ocjco`QIn=#<W}UG;=wPjC&)c?9W*%0}7Ko69dII4SGd'
        '7SE3mX(F2Ydg-<!v2D-'
        '^pc$^%myE+PYqP#a^u=<7@$I;`ohBm=Pj+3*NswEL%_zYpp6{LNqH}Uu`$;XYtENNObE+6w7z71JhY)`I;>Yv}{Q>Hu_;!9Glf9s'
        'if^M>@!R7p!mt4o5kxA=Vd}xk9FVJa!b<J5N@?}_Ov3@3cku+ci;!{9Ha<mvW$Jl`qXg;PgkB^kg(5iut3ox*PwA~@6+RO(u&zKJ'
        'wBIaOsWfj$otRMjLN2Jvwes=f&1ya?@Nub*$fNDCF?4~qLIYB|&tMqlHI-'
        '1pIh1HLhuw+3XF}esjnybBI_E!L}qT#*?MT_W)%6wj-'
        '49^6$xC$7LdO7}Si&^?MyXp)4nnb>mxj<f$P6E?HqherrC@Zfs@mgO(cj0LZM8WhVhv(lO1W%$}<tZ}47SWW(Dp~<Iy8#t2M7=lr'
        'a=k>_0j9rHek-pRmir?oV7~T$(>n0mpqtbdH?1({fqY87UZw|O5)&CU&+f+!&m6PA@Vm@BVL8R1CvgNc8jdFAq=}(P#dUNL{5+Hy'
        'B>`OF)7a0k3dl%6xVn2*0oYQf>YcKozmw0?cpWYz&1z|0@@?f7Y+{vkG)k@49iY&^L_Z}2Ofy?|V?OnN^ZM{f@Rd+8CUGB^+o{|9'
        '=4C<a<PR6vJl2+*IoOW#W@zKOE)R(odk;{U@Ys?=w+>lj-qmKvy0ah7QuSb#7`Q`4FZnHHV6$6)@K?(NiJv2cr@iR0MIPnv$GHif'
        'NPF2>#FG$S0+0srzFXe@ep$LSqmY4{pks0)3f&IU9|u%sX=+K*(hjC<I(8$j&muCmz{+#8^$9y5>@gaEx<f|ctZ!N`WJ2N>FnKVJ'
        '7qRrWNf73K23+{>2~F#$I>5vvImQF8Q-'
        'rCAkka)@9|nNl7p1}+*7r9{o?;mGN7$eKwlsxgX1pBg0hlX#TWeMxPj~d6@Dulj#N0rGiK(SErX>r6V3$d#HW41#bam!wLn4m*62'
        'ZRmB5&9inMd5qEo9GZD?Z(F=@1Dj8gtdXU+c9W9ZLwy4q_zazPyu|X!7MZinZ!<nTNoMy`z4i1L7QiBYs(?Mjtx^wV>ThC^90d+9'
        'aa507$V8lPOi=_0znsLZAgm`&qeUMVyo2+uaA6+Y4gbEeH62lN>%%P%8xv1wj&Pu$9OXr(hSR!VLsKR6zp$dZa_g--8M}EesAjAf'
        'Sa;lfrP&RK5~&P_E!lhTI5Tk9$w`qIFz>3dZkH+Dt{-c#NS5-'
        'Gx;7ID7C2Ml){vseb{aCjAjcKckO8P7{Sxq<HHWp~f~`820sOg8y-'
        'kPDIv|t;`F4>&V@1);^w@6De=IR(9NKBq@9xn9s|(YaaEPN0bLiqgGN}SQHkCoUeCubJpUZ`mOPN#5USxjYQV=5v2`Fno18UgNs|'
        'HT{;;8tdOwbz6)(mljdpbrN)yL5vnzG2^wf6w;Q37^WIATmoYM;{;e>vJnrlE8ioNZq)w^=@*h>zRjZp}+3M11&;V@(&$51<@+{V'
        'R{K6dZ78{ET1573#@pNRizdl%<c4OHrEV0V`MTld7l)knBD(}OB<k4|@0;~t2+iIJf)T-'
        'JHE<xwLBL0XIF4o~qbf0Jyrx;WO1~l=mc>QTi3Z0+Z(r(FHzkE|46MLugZvissPWRXDC{dR+wL)j+MG#L+<;)Dl?rzl|91<Vck03'
        'XW`5t3_Ime${c>x!Yvr(hccG9T5X0<4a`U9gl!hL&eCxH(mlsots>%Z5bTJjkgWQJv`mq&E;6ik}b#n-'
        'J>gvRJu`Ie*g1?*@!7tLl$4D#hr*hspUR*dcBMDlHdS!w;u;GM0(idu-'
        '|`9gF^?H(tN#Ctm+_ujR(VSrZFs2qZ~biZxO1DLleo)?3y6JdMJsF2&vjoDLl;A<#*T=_zGo@ukC+P$><21^TQsUxev<-'
        '6M}HsDCF!YGpg4FE}O9B0PBB-Xy~HJnSQsb2O4x|I`wb4J)luX=#!<-'
        '+?!n8GR?aFEU8=CLvRe3_5Gk}?p~CLV+wx}TT4*$1f=#4)QZbmi1J#@dmXe}K`4c(laMQ+!XSU77DdJ}N6f(XmieR7^;}+mZcUEV'
        '5UEmbV-!17-'
        'LYi$w0Jv3zI%4v+baoTFeosr<qbK2cJw{O1{e68WZyyw2|?uSU;0ZiDD?Rkh%ZF5XdA#8=DlT)wxV2HW`*8L0H>^%D4Ctt;b!oEs'
        'w%$LYyZrVxsQTsolCffB)=?HQKt`(6*lwRd*rly53bw%KoTFR8r&GE!$wTmj1$nw9-'
        '0YS@xjz2EVhwW4UemamTQMX;C~0{0k$P(eY;%QN983F~<t*|T)D^sW?RpWu2*qrc)NY}QnL9I9ECPm}?Yo?%>|iDIG7K08vM^AU#'
        'q4Npibf_=0i#SvN7@c(;x%3y&bzEl>VKh;y^O$Lc9BMj`1=89lGLE1kH))JI~LD6Cmo`=Iu4@k^LQG#e^w(3l97~vQoD5cZ$_Xq$'
        'KHl2{OP3=NNIyYi;{~9dx+(HU{xYcD0EuQf0)3NI#3J`}zmq;H9dZfR=mhwXT+1vtoU8=Tb(1&8ngCee*5}MDsaX7puLdWlE_SsN'
        'eK1I$Apn#k>RcS^@e6Alx<U{#S@MXF1vG(r3Y6d_{aKfsUF|S4>d<-'
        '+mpfUuo?wEeY@kYMz!@b%0f*Q2^TYer^IS=JpQXc$OW}py~7P%FGlp}W&J~nA*%0Tv?jgy^v{&L@DJj~%nk+hDo*X9f}PKXI<vl0'
        'u{CDdxL2d`DJ!D2H=Vym#pmZLRgEIH2U!L2vzV=J2JEUX3Uk^XCiY-'
        '8~07>T#w5eESZ<8A^958TgLIN<}yqBCpf5Xpm#_#vzIP46J}cOC1G$}@pT5R5{Y1=9Ec00000'
    ),
}
for relative, encoded in ICONES_INTERNOS.items():
    target = RES / relative
    if not target.is_file():
        raise RuntimeError(f'Arquivo do tema-base não encontrado: {target}')
    source = BASE / 'assets' / relative
    target.write_bytes(source.read_bytes() if source.is_file() else base64.b85decode(encoded))

# Verificação sintática básica dos arquivos XML que acabamos de gerar/editar.
for path in [RES / 'values' / 'strings.xml', RES / 'values-pt-rBR' / 'strings.xml',
             RES / 'values' / 'memk_strings.xml', RES / 'values-pt-rBR' / 'memk_strings.xml',
             RES / 'drawable' / 'memk_banner.xml', RES / 'drawable' / 'memk_launcher_foreground.xml',
             RES / 'layout' / 'fragment_launcher.xml', RES / 'layout-land' / 'fragment_launcher.xml']:
    ET.parse(path)
print('✅ MEMK JAVA aplicado! APK de teste: :app_pojavlauncher:assembleDebug')
