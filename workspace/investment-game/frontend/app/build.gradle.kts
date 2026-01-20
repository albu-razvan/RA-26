plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "se.chalmers.investmentgame"
    //noinspection GradleDependency
    compileSdk = 36

    defaultConfig {
        applicationId = "se.chalmers.investmentgame"
        minSdk = 22
        //noinspection ExpiredTargetSdkVersion
        targetSdk = 22
        versionCode = 1
        versionName = "1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
}

dependencies {
    implementation(libs.material)
    implementation(libs.constraintlayout)

    implementation(libs.gson)
}