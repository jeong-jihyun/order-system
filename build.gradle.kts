plugins {
    java
    id("org.springframework.boot") version "3.2.3" apply false
    id("io.spring.dependency-management") version "1.1.4" apply false
}

allprojects {
    repositories { mavenCentral() }
}

subprojects {
    apply(plugin = "java")
    java { sourceCompatibility = JavaVersion.VERSION_17 }
}
