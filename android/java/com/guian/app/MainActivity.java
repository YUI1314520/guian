package com.guian.app;

import android.app.Activity;
import android.os.Bundle;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.JavascriptInterface;
import android.os.Build;
import android.view.View;
import android.webkit.WebViewClient;
import android.graphics.Color;

/** 归岸：一个 WebView 外壳，页面全部打包在 assets/www 里，完全离线。 */
public class MainActivity extends Activity {

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setTextZoom(100);
        s.setMediaPlaybackRequiresUserGesture(false);
        // 关掉 WebView 的「强制深色」：页面自己有一套 MD3 深色 token，
        // 不让系统再叠一层算法反色，否则浅色主题在深色系统下会被染黑。
        if (Build.VERSION.SDK_INT >= 33) {
            s.setAlgorithmicDarkeningAllowed(false);
        } else if (Build.VERSION.SDK_INT >= 29) {
            s.setForceDark(WebSettings.FORCE_DARK_OFF);
        }

        web.setBackgroundColor(Color.parseColor("#F5FBF6"));
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new Bridge(), "AndroidChrome");
        web.setOverScrollMode(WebView.OVER_SCROLL_NEVER);
        web.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        // 去掉点击元素时的系统高亮块（老的 WebView 会用主题色画一个蓝色方块）
        if (Build.VERSION.SDK_INT >= 26) {
            web.setDefaultFocusHighlightEnabled(false);
        }
        web.setFocusable(true);
        web.setFocusableInTouchMode(true);
        web.setHapticFeedbackEnabled(false);

        setContentView(web);
        web.loadUrl("file:///android_asset/www/index.html");
    }

    /** 供网页调用：跟随页面主题切换状态栏 / 导航栏底色。 */
    private class Bridge {
        @JavascriptInterface
        public void setChrome(final String bg, final boolean dark) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    int color = Color.parseColor(bg);
                    getWindow().setStatusBarColor(color);
                    getWindow().setNavigationBarColor(color);

                    View decor = getWindow().getDecorView();
                    int flags = decor.getSystemUiVisibility();
                    if (dark) {
                        flags &= ~View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                        flags &= ~View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                    } else {
                        flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
                        if (Build.VERSION.SDK_INT >= 26) flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
                    }
                    decor.setSystemUiVisibility(flags);
                }
            });
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        if (web != null) web.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) web.onResume();
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.loadUrl("about:blank");
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
